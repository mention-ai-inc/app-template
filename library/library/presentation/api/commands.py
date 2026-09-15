import json
import logging
import os
from collections.abc import AsyncIterator

from fastapi import Header

from library.application.ports.eventbus import OutboundMessage
from library.domain.value_objects.common import Service
from library.logs import SIMPLE_LOGGER_NAME, add_log_context
from library.providers.registry import get_cloud_provider

logger = logging.getLogger(SIMPLE_LOGGER_NAME)


async def publish_command_result(
    command_id: str | None = None,
    invoker: Service = Header(alias="x-invoking-service"),
    retry_count: int = Header(default=0, alias="x-cloudtasks-taskretrycount"),
) -> AsyncIterator[None]:
    thrown: Exception | None = None

    if command_id is not None:
        attempt = retry_count + 1
        add_log_context(invoker=invoker, attempt=attempt, command_id=command_id)

    try:
        yield
    except Exception as error:
        thrown = error

    if command_id is None:
        return

    message: OutboundMessage = {
        "data": json.dumps({"command_id": command_id, "success": thrown is None, "attempt": retry_count + 1}),
        "attributes": {"service": invoker, "event": "AcknowledgeCommandResult"},
    }
    await (
        get_cloud_provider()
        .event_bus()
        .publish(topic_name=os.getenv("FEATURE_ENVIRONMENT", "") + "command_results", messages=[message])
    )

    if thrown is not None:
        raise thrown
