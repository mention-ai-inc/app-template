import json
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi import FastAPI, Request
from pydantic import BaseModel

from library.application.ports.cache import IAsyncCache
from library.domain.events.base import EventPayload
from library_provider_aws.changefeed import DynamoDbStreamRecord
from library_provider_aws.events import SnsMessageParser, SnsNotification


class Note(BaseModel):
    id: str
    title: str
    revisions: int


def _request(payload: Any) -> Request:
    body = json.dumps(payload).encode()

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": body, "more_body": False}

    scope: dict[str, Any] = {
        "type": "http",
        "method": "POST",
        "path": "/triggers/index_note",
        "headers": [(b"content-type", b"application/json")],
        "app": FastAPI(),
    }
    return Request(scope, receive)


def _record(new_image: dict[str, Any] | None) -> dict[str, Any]:
    stream: dict[str, Any] = {"Keys": {"pk": {"S": "notes_note#note_1"}}}
    if new_image is not None:
        stream["NewImage"] = new_image
    return {"eventName": "MODIFY", "dynamodb": stream}


NEW_IMAGE: dict[str, Any] = {
    "pk": {"S": "notes_note#note_1"},
    "sk": {"S": "root"},
    "_collection": {"S": "notes_note"},
    "_document_id": {"S": "note_1"},
    "_version": {"N": "3"},
    "_subcollection_metadata": {"M": {}},
    "id": {"S": "note_1"},
    "title": {"S": "A note"},
    "revisions": {"N": "2"},
}


class TestDocumentChangeFeed:
    async def test_a_stream_record_becomes_the_document_model(self) -> None:
        feed = DynamoDbStreamRecord(Note)

        assert await feed(_request(_record(NEW_IMAGE))) == Note(id="note_1", title="A note", revisions=2)

    async def test_a_pipes_batch_is_read_from_its_first_record(self) -> None:
        feed = DynamoDbStreamRecord(Note)

        assert await feed(_request([_record(NEW_IMAGE)])) == Note(id="note_1", title="A note", revisions=2)

    async def test_a_lambda_style_envelope_is_understood(self) -> None:
        feed = DynamoDbStreamRecord(Note)

        assert await feed(_request({"Records": [_record(NEW_IMAGE)]})) == Note(id="note_1", title="A note", revisions=2)

    async def test_a_removal_carries_no_new_image_and_yields_nothing(self) -> None:
        feed = DynamoDbStreamRecord(Note)

        assert await feed(_request(_record(None))) is None

    async def test_a_record_that_does_not_fit_the_model_yields_nothing(self) -> None:
        feed = DynamoDbStreamRecord(Note)

        assert await feed(_request(_record({"id": {"S": "note_1"}}))) is None


class NoteCreated(EventPayload):
    note_id: str


class UnusedCache:
    async def get(self, name: str, /) -> bytes | None:  # noqa: ARG002
        return None

    async def set(
        self,
        name: str,  # noqa: ARG002
        value: bytes,  # noqa: ARG002
        /,
        *,
        ex: int | None = None,  # noqa: ARG002
        px: int | None = None,  # noqa: ARG002
        nx: bool | None = None,  # noqa: ARG002
        xx: bool | None = None,  # noqa: ARG002
    ) -> bool | None:
        return True

    async def delete(self, *names: str) -> int:  # noqa: ARG002
        return 0


class TestSnsMessageParser:
    @pytest.fixture
    def parser(self) -> SnsMessageParser[NoteCreated]:
        cache: IAsyncCache = UnusedCache()
        return SnsMessageParser(data_models=[NoteCreated], cache=cache)

    async def test_an_sns_notification_becomes_an_inbound_event(self, parser: SnsMessageParser[NoteCreated]) -> None:
        notification = SnsNotification.model_validate(
            {
                "Type": "Notification",
                "MessageId": "message-1",
                "TopicArn": "arn:aws:sns:us-east-1:123456789012:notes",
                "Message": "eyJub3RlX2lkIjogIm5vdGVfMSJ9",
                "Timestamp": datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
                "MessageAttributes": {
                    "event": {"Type": "String", "Value": "NoteCreated"},
                    "service": {"Type": "String", "Value": "notes"},
                },
            }
        )

        event = await parser(notification)

        assert event.data == NoteCreated(note_id="note_1")
        assert event.message_id == "message-1"
        assert event.attributes.event == "NoteCreated"
        assert event.publish_time == datetime(2026, 1, 1, tzinfo=UTC)
