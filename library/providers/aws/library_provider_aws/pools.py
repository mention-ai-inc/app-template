import asyncio
import json
import logging
import os
import signal
from dataclasses import dataclass
from typing import Any, Literal, cast

import httpx
from fastapi import FastAPI

from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType
from library.logs import SIMPLE_LOGGER_NAME
from library_provider_aws.clients import client

type ComponentKind = Literal["executor", "listener", "trigger"]

QUEUE_ENVIRONMENT_VARIABLES: dict[ComponentKind, str] = {
    "executor": "SQS_EXECUTOR_QUEUES_JSON",
    "listener": "SQS_LISTENER_QUEUES_JSON",
    "trigger": "SQS_TRIGGER_QUEUES_JSON",
}
POOL_BASE_URL = "http://pool.invalid"
DEFAULT_CONCURRENCY = 80
DEFAULT_HANDLER_TIMEOUT = 60.0
RECEIVE_WAIT_SECONDS = 20
RECEIVE_BATCH_SIZE = 10


@dataclass(frozen=True)
class QueueSubscription:
    queue_url: str
    path: str
    kind: ComponentKind


class SqsPoolDriver:
    def __init__(self) -> None:
        self._logger = logging.getLogger(SIMPLE_LOGGER_NAME)

    async def __call__(self, *, app: FastAPI, routes: dict[str, str]) -> None:
        subscriptions = self.subscriptions(routes)
        if len(subscriptions) == 0:
            raise InfrastructureError(
                error_type=InfrastructureErrorType.ENVIRONMENT_ERROR,
                message=(
                    "No SQS queue is declared for any route this pool serves. Expected one of "
                    f"{sorted(QUEUE_ENVIRONMENT_VARIABLES.values())} to name a queue for {sorted(routes)}"
                ),
            )

        stopping = asyncio.Event()
        self.__listen_for_shutdown(stopping)
        permits = asyncio.Semaphore(self.concurrency())

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url=POOL_BASE_URL, timeout=self.handler_timeout()
        ) as dispatcher:
            async with asyncio.TaskGroup() as pollers:
                for subscription in subscriptions:
                    pollers.create_task(
                        self.__poll(subscription, dispatcher=dispatcher, stopping=stopping, permits=permits)
                    )

    def subscriptions(self, routes: dict[str, str], /) -> list[QueueSubscription]:
        found: list[QueueSubscription] = []

        for kind, variable in QUEUE_ENVIRONMENT_VARIABLES.items():
            declared: dict[str, Any] = json.loads(os.getenv(variable, "{}"))
            for key, value in declared.items():
                path = routes.get(key.split(":", 1)[-1])
                if path is None:
                    continue
                queue_urls: list[Any] = value if isinstance(value, list) else [value]
                found.extend(
                    QueueSubscription(queue_url=str(queue_url), path=path, kind=kind) for queue_url in queue_urls
                )

        return found

    def concurrency(self) -> int:
        return int(os.getenv("CONTAINER_CONCURRENCY", str(DEFAULT_CONCURRENCY)))

    def handler_timeout(self) -> float:
        return float(os.getenv("HANDLER_TIMEOUT", str(DEFAULT_HANDLER_TIMEOUT)))

    async def __poll(
        self,
        subscription: QueueSubscription,
        /,
        *,
        dispatcher: httpx.AsyncClient,
        stopping: asyncio.Event,
        permits: asyncio.Semaphore,
    ) -> None:
        while not stopping.is_set():
            messages = await self.__receive(subscription, stopping=stopping)
            if len(messages) == 0:
                continue

            async with asyncio.TaskGroup() as handlers:
                for message in messages:
                    handlers.create_task(
                        self.__handle(message, subscription=subscription, dispatcher=dispatcher, permits=permits)
                    )

    async def __receive(self, subscription: QueueSubscription, /, *, stopping: asyncio.Event) -> list[dict[str, Any]]:
        async with client("sqs") as sqs:
            receiving = asyncio.ensure_future(
                sqs.receive_message(
                    QueueUrl=subscription.queue_url,
                    MaxNumberOfMessages=RECEIVE_BATCH_SIZE,
                    WaitTimeSeconds=RECEIVE_WAIT_SECONDS,
                    MessageAttributeNames=["All"],
                )
            )
            stopped = asyncio.ensure_future(stopping.wait())
            await asyncio.wait({receiving, stopped}, return_when=asyncio.FIRST_COMPLETED)

            stopped.cancel()
            if not receiving.done():
                receiving.cancel()
                return []

            return list((await receiving).get("Messages", []))

    async def __handle(
        self,
        message: dict[str, Any],
        /,
        *,
        subscription: QueueSubscription,
        dispatcher: httpx.AsyncClient,
        permits: asyncio.Semaphore,
    ) -> None:
        async with permits:
            try:
                delivered = await self.__deliver(message, subscription=subscription, dispatcher=dispatcher)
            except Exception as error:
                self._logger.error(f"{subscription.path} raised while handling an SQS message: {error}")
                return

        if delivered:
            await self.__acknowledge(message, subscription=subscription)

    async def __deliver(
        self, message: dict[str, Any], /, *, subscription: QueueSubscription, dispatcher: httpx.AsyncClient
    ) -> bool:
        body = str(message.get("Body", ""))

        if subscription.kind == "executor":
            return await self.__post_command(body, subscription=subscription, dispatcher=dispatcher)

        for payload in self.__payloads(body, subscription=subscription):
            response = await dispatcher.post(
                subscription.path, content=payload, headers={"content-type": "application/json"}
            )
            if response.is_error:
                self._logger.error(
                    f"{subscription.path} answered {response.status_code}; leaving the message for redrive"
                )
                return False

        return True

    async def __post_command(
        self, body: str, /, *, subscription: QueueSubscription, dispatcher: httpx.AsyncClient
    ) -> bool:
        envelope: dict[str, Any] = json.loads(body)
        declared: dict[str, str] = envelope.get("headers") or {}
        headers: dict[str, str] = {**declared, "content-type": "application/json"}
        response = await dispatcher.post(
            subscription.path,
            params=envelope.get("params") or {},
            json=envelope.get("body") or {},
            headers=headers,
        )

        if response.is_error:
            self._logger.error(f"{subscription.path} answered {response.status_code}; leaving the message for redrive")
            return False
        return True

    def __payloads(self, body: str, /, *, subscription: QueueSubscription) -> list[str]:
        if subscription.kind != "trigger":
            return [body]

        batch: Any = json.loads(body)
        if not isinstance(batch, list):
            return [body]
        return [json.dumps(record) for record in cast(list[Any], batch)]

    async def __acknowledge(self, message: dict[str, Any], /, *, subscription: QueueSubscription) -> None:
        async with client("sqs") as sqs:
            await sqs.delete_message(QueueUrl=subscription.queue_url, ReceiptHandle=message["ReceiptHandle"])

    def __listen_for_shutdown(self, stopping: asyncio.Event, /) -> None:
        loop = asyncio.get_running_loop()
        for received in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(received, stopping.set)
            except (NotImplementedError, ValueError):
                self._logger.warning(f"This platform cannot listen for {received.name}; the pool will not drain")
