import asyncio
import json
import logging
import os
import signal
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, cast

import httpx
from azure.servicebus import ServiceBusReceivedMessage, ServiceBusSubQueue
from azure.servicebus.aio import AutoLockRenewer, ServiceBusReceiver
from fastapi import FastAPI

from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType
from library.logs import SIMPLE_LOGGER_NAME
from library.presentation.api.environment import ComponentType
from library_provider_azure.clients import AzureClients
from library_provider_azure.documents import DOCUMENT_TYPE_FIELD
from library_provider_azure.messaging import HEADERS_PROPERTY, PARAMS_PROPERTY
from library_provider_azure.settings import (
    CHANGE_FEED_TRIGGERS_JSON,
    SERVICE_BUS_QUEUES_JSON,
    SERVICE_BUS_SUBSCRIPTIONS_JSON,
    routing_table,
)

POOL_BASE_URL = "http://pool.invalid"
MAX_CONCURRENT_MESSAGES = 8
MAX_LOCK_RENEWAL_SECONDS = 3600
RECEIVE_WAIT_SECONDS = 5
CHANGE_FEED_POLL_SECONDS = 2
DRAIN_TIMEOUT_SECONDS = 30
CONTINUATION_FIELD = "continuation"
RETRY_COUNT_HEADER = "x-cloudtasks-taskretrycount"

logger = logging.getLogger(SIMPLE_LOGGER_NAME)


@dataclass(frozen=True)
class ServiceBusSource:
    route_name: str
    path: str
    queue_name: str | None = None
    topic_name: str | None = None
    subscription_name: str | None = None
    dead_letter: bool = False


@dataclass(frozen=True)
class ChangeFeedSource:
    route_name: str
    path: str
    container_name: str
    lease_container_name: str
    document_type: str


def decode_property(value: Any, /) -> str:
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode()
    return str(value)


def read_properties(message: ServiceBusReceivedMessage, /) -> dict[str, str]:
    raw = cast(Mapping[Any, Any] | None, message.application_properties) or {}
    return {decode_property(key): decode_property(value) for key, value in raw.items()}


def read_body(message: ServiceBusReceivedMessage, /) -> str:
    body = message.body
    if isinstance(body, (bytes, bytearray)):
        return bytes(body).decode()
    if isinstance(body, str):
        return body
    return b"".join(bytes(part) for part in cast(Iterable[Any], body)).decode()


class AzurePoolDriver:
    def __init__(
        self,
        *,
        max_concurrency: int = MAX_CONCURRENT_MESSAGES,
        max_lock_renewal_seconds: int = MAX_LOCK_RENEWAL_SECONDS,
        drain_timeout_seconds: int = DRAIN_TIMEOUT_SECONDS,
    ) -> None:
        self._max_concurrency = max_concurrency
        self._max_lock_renewal_seconds = max_lock_renewal_seconds
        self._drain_timeout_seconds = drain_timeout_seconds

    async def __call__(self, *, app: FastAPI, routes: dict[str, str]) -> None:
        component = self.__component_type()
        stopping = asyncio.Event()
        self.__stop_on_termination(stopping)

        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport, base_url=POOL_BASE_URL, timeout=httpx.Timeout(None)
            ) as client:
                if component is ComponentType.TRIGGER:
                    await self.__consume_change_feeds(client=client, routes=routes, stopping=stopping)
                else:
                    await self.__consume_service_bus(
                        client=client, routes=routes, component=component, stopping=stopping
                    )

    def service_bus_sources(self, *, routes: dict[str, str], component: ComponentType) -> list[ServiceBusSource]:
        if component is ComponentType.EXECUTOR:
            return self.__queue_sources(routes)
        if component is ComponentType.LISTENER:
            return self.__subscription_sources(routes)
        raise InfrastructureError(
            error_type=InfrastructureErrorType.ENVIRONMENT_ERROR,
            message=f"A Service Bus pool hosts executors or listeners, not {component}",
        )

    def change_feed_sources(self, *, routes: dict[str, str]) -> list[ChangeFeedSource]:
        sources: list[ChangeFeedSource] = []
        for routing in routing_table(CHANGE_FEED_TRIGGERS_JSON).values():
            trigger_name = routing["trigger_name"]
            path = routes.get(trigger_name)
            if path is None:
                continue
            sources.append(
                ChangeFeedSource(
                    route_name=trigger_name,
                    path=path,
                    container_name=routing["container_name"],
                    lease_container_name=routing["lease_container_name"],
                    document_type=routing["document_type"],
                )
            )
        return self.__guard_sources(sources, component=ComponentType.TRIGGER)

    def to_request(
        self, *, message: ServiceBusReceivedMessage, source: ServiceBusSource, component: ComponentType
    ) -> tuple[str, str, dict[str, str]]:
        properties = read_properties(message)

        if component is ComponentType.EXECUTOR:
            params = cast(dict[str, str], json.loads(properties.get(PARAMS_PROPERTY, "{}")))
            headers = cast(dict[str, str], json.loads(properties.get(HEADERS_PROPERTY, "{}")))
            query = "&".join(f"{key}={value}" for key, value in params.items())
            path = f"{source.path}?{query}" if query else source.path
            retry_count = max((message.delivery_count or 1) - 1, 0)
            return (
                path,
                read_body(message),
                {**headers, "content-type": "application/json", RETRY_COUNT_HEADER: str(retry_count)},
            )

        enqueued_at = message.enqueued_time_utc or datetime.now(UTC)
        envelope = {
            "data": read_body(message),
            "attributes": properties,
            "message_id": message.message_id or "",
            "publish_time": enqueued_at.isoformat(),
        }
        return source.path, json.dumps(envelope), {"content-type": "application/json"}

    def __component_type(self) -> ComponentType:
        raw = os.getenv("COMPONENT_TYPE", "")
        try:
            return ComponentType(raw)
        except ValueError as error:
            raise InfrastructureError(
                error_type=InfrastructureErrorType.ENVIRONMENT_ERROR,
                message=f"COMPONENT_TYPE must name the kind of pool this process hosts, not {raw!r}",
            ) from error

    def __stop_on_termination(self, stopping: asyncio.Event, /) -> None:
        loop = asyncio.get_running_loop()
        for termination_signal in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(termination_signal, stopping.set)
            except (NotImplementedError, RuntimeError, ValueError):
                logger.warning(f"Cannot install a handler for {termination_signal}; the pool will not drain cleanly")

    def __queue_sources(self, routes: dict[str, str], /) -> list[ServiceBusSource]:
        sources: list[ServiceBusSource] = []
        for key, queue_name in routing_table(SERVICE_BUS_QUEUES_JSON).items():
            command_name = key.split(":", 1)[-1]
            path = routes.get(command_name)
            if path is None:
                continue
            sources.append(ServiceBusSource(route_name=command_name, path=path, queue_name=queue_name))
        return self.__guard_sources(sources, component=ComponentType.EXECUTOR)

    def __subscription_sources(self, routes: dict[str, str], /) -> list[ServiceBusSource]:
        sources: list[ServiceBusSource] = []
        for key, subscriptions in routing_table(SERVICE_BUS_SUBSCRIPTIONS_JSON).items():
            listener_name = key.split(":", 1)[-1]
            path = routes.get(listener_name)
            if path is None:
                continue
            for subscription in cast(list[dict[str, str]], subscriptions):
                sources.append(
                    ServiceBusSource(
                        route_name=listener_name,
                        path=path,
                        topic_name=subscription["topic_name"],
                        subscription_name=subscription["subscription_name"],
                    )
                )
                dead_letter_path = routes.get(f"{listener_name}_dead_letter")
                if dead_letter_path is not None:
                    sources.append(
                        ServiceBusSource(
                            route_name=f"{listener_name}_dead_letter",
                            path=dead_letter_path,
                            topic_name=subscription["topic_name"],
                            subscription_name=subscription["subscription_name"],
                            dead_letter=True,
                        )
                    )
        return self.__guard_sources(sources, component=ComponentType.LISTENER)

    def __guard_sources[SourceT](self, sources: list[SourceT], /, *, component: ComponentType) -> list[SourceT]:
        if len(sources) == 0:
            raise InfrastructureError(
                error_type=InfrastructureErrorType.ENVIRONMENT_ERROR,
                message=(
                    f"No {component} in this pool has anything to consume. The routing table names no source "
                    "that matches a route on this app."
                ),
            )
        return sources

    async def __consume_service_bus(
        self, *, client: httpx.AsyncClient, routes: dict[str, str], component: ComponentType, stopping: asyncio.Event
    ) -> None:
        sources = self.service_bus_sources(routes=routes, component=component)
        semaphore = asyncio.Semaphore(self._max_concurrency)

        async with AutoLockRenewer(max_lock_renewal_duration=self._max_lock_renewal_seconds) as renewer:
            await asyncio.gather(
                *(
                    self.__pump_service_bus(
                        client=client,
                        source=source,
                        component=component,
                        renewer=renewer,
                        semaphore=semaphore,
                        stopping=stopping,
                    )
                    for source in sources
                )
            )

    async def __pump_service_bus(
        self,
        *,
        client: httpx.AsyncClient,
        source: ServiceBusSource,
        component: ComponentType,
        renewer: AutoLockRenewer,
        semaphore: asyncio.Semaphore,
        stopping: asyncio.Event,
    ) -> None:
        inflight: set[asyncio.Task[None]] = set()

        async with self.__receiver(source) as receiver:
            while not stopping.is_set():
                messages = await receiver.receive_messages(
                    max_message_count=self._max_concurrency, max_wait_time=RECEIVE_WAIT_SECONDS
                )
                for message in messages:
                    renewer.register(receiver, message, max_lock_renewal_duration=self._max_lock_renewal_seconds)
                    await semaphore.acquire()
                    task = asyncio.create_task(
                        self.__deliver(
                            client=client,
                            receiver=receiver,
                            message=message,
                            source=source,
                            component=component,
                            semaphore=semaphore,
                        )
                    )
                    inflight.add(task)
                    task.add_done_callback(inflight.discard)

            if inflight:
                await asyncio.wait(inflight, timeout=self._drain_timeout_seconds)

    def __receiver(self, source: ServiceBusSource, /) -> ServiceBusReceiver:
        sub_queue = ServiceBusSubQueue.DEAD_LETTER if source.dead_letter else None
        service_bus = AzureClients.service_bus()

        if source.queue_name is not None:
            return service_bus.get_queue_receiver(queue_name=source.queue_name, sub_queue=sub_queue)

        return service_bus.get_subscription_receiver(
            topic_name=source.topic_name or "",
            subscription_name=source.subscription_name or "",
            sub_queue=sub_queue,
        )

    async def __deliver(
        self,
        *,
        client: httpx.AsyncClient,
        receiver: ServiceBusReceiver,
        message: ServiceBusReceivedMessage,
        source: ServiceBusSource,
        component: ComponentType,
        semaphore: asyncio.Semaphore,
    ) -> None:
        try:
            path, content, headers = self.to_request(message=message, source=source, component=component)
            response = await client.post(path, content=content, headers=headers)

            if response.is_success:
                await receiver.complete_message(message)
            else:
                logger.error(f"{source.route_name} returned {response.status_code}; abandoning for redelivery")
                await receiver.abandon_message(message)
        except Exception as error:
            logger.error(f"{source.route_name} raised {error}; abandoning for redelivery")
            await receiver.abandon_message(message)
        finally:
            semaphore.release()

    async def __consume_change_feeds(
        self, *, client: httpx.AsyncClient, routes: dict[str, str], stopping: asyncio.Event
    ) -> None:
        sources = self.change_feed_sources(routes=routes)
        await asyncio.gather(
            *(self.__pump_change_feed(client=client, source=source, stopping=stopping) for source in sources)
        )

    async def __pump_change_feed(
        self, *, client: httpx.AsyncClient, source: ChangeFeedSource, stopping: asyncio.Event
    ) -> None:
        container = AzureClients.container(source.container_name)
        continuation = await self.__read_continuation(source)

        while not stopping.is_set():
            feed = (
                container.query_items_change_feed(continuation=continuation)
                if continuation is not None
                else container.query_items_change_feed(start_time="Beginning")
            )

            delivered = 0
            async for item in feed:
                if item.get(DOCUMENT_TYPE_FIELD) != source.document_type:
                    continue
                response = await client.post(source.path, json=item)
                if not response.is_success:
                    logger.error(f"{source.route_name} returned {response.status_code}; the change feed will retry")
                    break
                delivered += 1
            else:
                continuation = cast(
                    str | None, container.client_connection.last_response_headers.get("etag", continuation)
                )
                await self.__write_continuation(source, continuation=continuation)

            if delivered == 0:
                await asyncio.sleep(CHANGE_FEED_POLL_SECONDS)

    async def __read_continuation(self, source: ChangeFeedSource, /) -> str | None:
        leases = AzureClients.container(source.lease_container_name)
        items = [
            item
            async for item in leases.query_items(
                query="SELECT * FROM c WHERE c.id = @id", parameters=[{"name": "@id", "value": source.route_name}]
            )
        ]
        return cast(str | None, items[0].get(CONTINUATION_FIELD)) if items else None

    async def __write_continuation(self, source: ChangeFeedSource, /, *, continuation: str | None) -> None:
        if continuation is None:
            return
        await AzureClients.container(source.lease_container_name).upsert_item(
            body={"id": source.route_name, CONTINUATION_FIELD: continuation}
        )
