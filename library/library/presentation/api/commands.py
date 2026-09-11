import json
import logging
import os
from collections.abc import AsyncIterator

from fastapi import Header

from library.domain.value_objects.common import Service
from library.infrastructure.cloud.pubsub import Message, Pubsub
from library.logs import SIMPLE_LOGGER_NAME, add_log_context

pubsub = Pubsub()
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

    message: Message = {
        "data": json.dumps({"command_id": command_id, "success": thrown is None, "attempt": retry_count + 1}),
        "attributes": {"service": invoker, "event": "AcknowledgeCommandResult"},
    }
    await pubsub.publish(topic_name=os.getenv("FEATURE_ENVIRONMENT", "") + "command_results", messages=[message])

    if thrown is not None:
        raise thrown
