import base64
import json
import uuid
from datetime import datetime
from typing import Any, cast
from urllib.parse import urlencode

from azure.servicebus import ServiceBusMessage

from library.application.ports.eventbus import OutboundMessage
from library.conventions import COMMAND_PATH_PREFIX
from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType
from library_provider_azure.clients import AzureClients
from library_provider_azure.settings import (
    SERVICE_BUS_NAMESPACE,
    SERVICE_BUS_QUEUES_JSON,
    required,
    route_key,
    routing_table,
)

ROUTE_PROPERTY = "route"
PARAMS_PROPERTY = "params"
HEADERS_PROPERTY = "headers"


def queue_name_for(*, service: str, task: str) -> str:
    queues = routing_table(SERVICE_BUS_QUEUES_JSON)
    queue_name = queues.get(route_key(service=service, name=task))

    if not isinstance(queue_name, str):
        raise InfrastructureError(
            error_type=InfrastructureErrorType.CLOUD_ERROR,
            message=f"No Service Bus queue is declared for service={service} task={task}",
        )

    return queue_name


class ServiceBusEventBus:
    async def publish(self, *, topic_name: str, messages: list[OutboundMessage]) -> list[str]:
        if len(messages) == 0:
            return []

        message_ids: list[str] = []
        outbound: list[ServiceBusMessage] = []
        for message in messages:
            message_id = uuid.uuid4().hex
            message_ids.append(message_id)
            outbound.append(
                ServiceBusMessage(
                    body=base64.b64encode(message.get("data", "").encode()).decode(),
                    message_id=message_id,
                    content_type="text/plain",
                    application_properties=cast(dict[str | bytes, Any], dict(message.get("attributes", {}))),
                )
            )

        async with AzureClients.service_bus().get_topic_sender(topic_name=topic_name) as sender:
            await sender.send_messages(outbound)

        return message_ids


class ServiceBusTaskQueue:
    def get_url(self, *, service: str, task: str, params: dict[str, str] | None = None) -> str:
        queue_name = queue_name_for(service=service, task=task)
        query = "" if params is None else f"?{urlencode(params)}"
        return f"sb://{required(SERVICE_BUS_NAMESPACE)}/{queue_name}{COMMAND_PATH_PREFIX}/{task}{query}"

    async def add_task(
        self,
        *,
        service: str,
        task: str,
        body: dict[str, Any],
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        scheduled_time: datetime | None = None,
    ) -> None:
        properties: dict[str | bytes, Any] = {
            ROUTE_PROPERTY: task,
            PARAMS_PROPERTY: json.dumps(params or {}),
            HEADERS_PROPERTY: json.dumps(headers or {}),
        }
        message = ServiceBusMessage(
            body=json.dumps(body, default=str),
            message_id=uuid.uuid4().hex,
            content_type="application/json",
            application_properties=properties,
        )

        if scheduled_time is not None:
            message.scheduled_enqueue_time_utc = scheduled_time

        async with AzureClients.service_bus().get_queue_sender(
            queue_name=queue_name_for(service=service, task=task)
        ) as sender:
            await sender.send_messages(message)
