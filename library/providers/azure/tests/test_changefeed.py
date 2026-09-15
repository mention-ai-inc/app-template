import json
from typing import Any

from fastapi import Request
from tests.infrastructure.persistence.mocks import MainId, SimpleEntity

from library.application.ports.documents import DocumentID
from library_provider_azure.changefeed import CosmosChangeFeedItem
from library_provider_azure.documents import to_cosmos_item
from library_provider_azure.events import ServiceBusMessageBody
from library_provider_azure.provider import AzureProvider


def to_request(body: dict[str, Any], /) -> Request:
    payload = json.dumps(body).encode()

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": payload, "more_body": False}

    return Request(
        {"type": "http", "method": "POST", "path": "/triggers/submit_command", "headers": []},
        receive,  # pyright: ignore[reportArgumentType]
    )


class TestTheChangeFeed:
    async def test_a_cosmos_item_arrives_as_the_entity_it_holds(self) -> None:
        entity = SimpleEntity(id=MainId(), name="hammer")
        record: dict[str, Any] = entity.model_dump(mode="json")
        item = to_cosmos_item(
            document_type="notes_simple",
            document_id=DocumentID(entity.id),
            partition_value="org_1",
            record=record,
        )

        read = await CosmosChangeFeedItem(SimpleEntity)(to_request({**item, "_etag": "etag-1", "_ts": 1}))

        assert read == entity

    async def test_an_item_that_is_not_the_expected_model_is_dropped_rather_than_raising(self) -> None:
        assert await CosmosChangeFeedItem(SimpleEntity)(to_request({"not": "an entity"})) is None

    def test_the_change_feed_is_not_a_cloud_event_envelope(self) -> None:
        assert isinstance(AzureProvider().change_feed(SimpleEntity), CosmosChangeFeedItem)


class TestTheMessageParser:
    def test_a_replayed_service_bus_message_is_the_envelope_the_parser_expects(self) -> None:
        body = ServiceBusMessageBody.model_validate(
            {
                "data": "cGF5bG9hZA==",
                "attributes": {"event": "NoteCreated", "service": "notes"},
                "message_id": "message-1",
                "publish_time": "2026-01-01T00:00:00+00:00",
            }
        )

        assert body.attributes["event"] == "NoteCreated"
        assert body.message_id == "message-1"
