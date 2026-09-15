import asyncio
import json
import signal
import uuid
from typing import Any

import boto3
import pytest
from conftest import REGION
from fastapi import FastAPI, Request, Response
from library_provider_aws.pools import SqsPoolDriver

from library.conventions import COMMAND_PATH_PREFIX, TRIGGER_PATH_PREFIX
from library.infrastructure.errors import InfrastructureError

COMMAND_QUEUE = "pool-notes-c-summarize-note"
TRIGGER_QUEUE = "pool-notes-t-index-note"
DRAIN_TIMEOUT_SECONDS = 20


class Pool:
    def __init__(self) -> None:
        self.app = FastAPI()
        self.commands: list[dict[str, Any]] = []
        self.triggers: list[Any] = []
        self.refuse = False

        @self.app.post(f"{COMMAND_PATH_PREFIX}/summarize_note", name="summarize_note")
        async def summarize_note(request: Request) -> Response:
            self.commands.append(
                {
                    "body": await request.json(),
                    "params": dict(request.query_params),
                    "request_id": request.headers.get("x-request-id"),
                }
            )
            return Response(status_code=503 if self.refuse else 204)

        @self.app.post(f"{TRIGGER_PATH_PREFIX}/index_note", name="index_note")
        async def index_note(request: Request) -> Response:
            self.triggers.append(await request.json())
            return Response(status_code=204)

    @property
    def routes(self) -> dict[str, str]:
        return {
            "summarize_note": f"{COMMAND_PATH_PREFIX}/summarize_note",
            "index_note": f"{TRIGGER_PATH_PREFIX}/index_note",
        }


@pytest.fixture
def sqs(moto_endpoint: str) -> Any:
    return boto3.client("sqs", endpoint_url=moto_endpoint, region_name=REGION)  # pyright: ignore[reportUnknownMemberType]


@pytest.fixture
def queues(sqs: Any, monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    suffix = uuid.uuid4().hex
    command_url = sqs.create_queue(QueueName=f"{COMMAND_QUEUE}-{suffix}")["QueueUrl"]
    trigger_url = sqs.create_queue(QueueName=f"{TRIGGER_QUEUE}-{suffix}")["QueueUrl"]

    monkeypatch.setenv("SQS_EXECUTOR_QUEUES_JSON", json.dumps({"notes:summarize_note": command_url}))
    monkeypatch.setenv("SQS_TRIGGER_QUEUES_JSON", json.dumps({"notes:index_note": trigger_url}))
    monkeypatch.setenv("SQS_LISTENER_QUEUES_JSON", "{}")
    monkeypatch.setenv("CONTAINER_CONCURRENCY", "4")

    return {"executor": command_url, "trigger": trigger_url}


async def _drain_pool(pool: Pool, *, until: Any) -> None:
    driver = asyncio.ensure_future(SqsPoolDriver()(app=pool.app, routes=pool.routes))

    async def _wait() -> None:
        while not until():
            await asyncio.sleep(0.05)

    try:
        await asyncio.wait_for(_wait(), timeout=DRAIN_TIMEOUT_SECONDS)
    finally:
        signal.raise_signal(signal.SIGTERM)
        await asyncio.wait_for(driver, timeout=DRAIN_TIMEOUT_SECONDS)


def _remaining(sqs: Any, queue_url: str) -> int:
    attributes = sqs.get_queue_attributes(
        QueueUrl=queue_url, AttributeNames=["ApproximateNumberOfMessages", "ApproximateNumberOfMessagesNotVisible"]
    )["Attributes"]
    return int(attributes["ApproximateNumberOfMessages"]) + int(attributes["ApproximateNumberOfMessagesNotVisible"])


class TestSubscriptions:
    def test_only_queues_whose_route_the_pool_serves_are_polled(self, queues: dict[str, str]) -> None:
        subscriptions = SqsPoolDriver().subscriptions({"summarize_note": f"{COMMAND_PATH_PREFIX}/summarize_note"})

        assert [subscription.queue_url for subscription in subscriptions] == [queues["executor"]]

    def test_a_pool_with_no_queue_for_any_route_refuses_to_start(self, queues: dict[str, str]) -> None:  # noqa: ARG002
        with pytest.raises(InfrastructureError):
            asyncio.run(SqsPoolDriver()(app=FastAPI(), routes={"nothing": "/commands/nothing"}))

    def test_the_concurrency_bound_comes_from_the_environment(self, queues: dict[str, str]) -> None:  # noqa: ARG002
        assert SqsPoolDriver().concurrency() == 4


class TestReplayingThePush:
    async def test_a_command_reaches_its_route_with_body_params_and_headers(
        self, sqs: Any, queues: dict[str, str]
    ) -> None:
        pool = Pool()
        sqs.send_message(
            QueueUrl=queues["executor"],
            MessageBody=json.dumps(
                {
                    "service": "notes",
                    "task": "summarize_note",
                    "body": {"note_id": "note_1"},
                    "params": {"page": "2"},
                    "headers": {"x-request-id": "req_1"},
                    "scheduled_time": None,
                }
            ),
        )

        await _drain_pool(pool, until=lambda: len(pool.commands) == 1)

        assert pool.commands == [{"body": {"note_id": "note_1"}, "params": {"page": "2"}, "request_id": "req_1"}]

    async def test_a_handled_command_is_deleted_from_the_queue(self, sqs: Any, queues: dict[str, str]) -> None:
        pool = Pool()
        sqs.send_message(
            QueueUrl=queues["executor"],
            MessageBody=json.dumps({"service": "notes", "task": "summarize_note", "body": {}}),
        )

        await _drain_pool(pool, until=lambda: len(pool.commands) == 1)

        assert _remaining(sqs, queues["executor"]) == 0

    async def test_a_refused_command_is_left_on_the_queue_for_redrive(self, sqs: Any, queues: dict[str, str]) -> None:
        pool = Pool()
        pool.refuse = True
        sqs.send_message(
            QueueUrl=queues["executor"],
            MessageBody=json.dumps({"service": "notes", "task": "summarize_note", "body": {}}),
        )

        await _drain_pool(pool, until=lambda: len(pool.commands) >= 1)

        assert _remaining(sqs, queues["executor"]) == 1

    async def test_a_batch_of_stream_records_becomes_one_delivery_each(self, sqs: Any, queues: dict[str, str]) -> None:
        pool = Pool()
        records = [
            {"eventName": "INSERT", "dynamodb": {"NewImage": {"id": {"S": "note_1"}}}},
            {"eventName": "MODIFY", "dynamodb": {"NewImage": {"id": {"S": "note_2"}}}},
        ]
        sqs.send_message(QueueUrl=queues["trigger"], MessageBody=json.dumps(records))

        await _drain_pool(pool, until=lambda: len(pool.triggers) == 2)

        assert pool.triggers == records
