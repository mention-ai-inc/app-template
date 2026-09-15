import base64
import json
import os
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

from library.application.ports.eventbus import OutboundMessage
from library.conventions import COMMAND_PATH_PREFIX
from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType
from library_provider_aws.clients import client, get_account_id, get_region, scope_resource_name

PUBLISH_BATCH_LIMIT = 10
MAXIMUM_DELAY_SECONDS = 900
POOL_HOST_SUFFIX = "ecs.internal"


class SnsEventBus:
    async def publish(self, *, topic_name: str, messages: list[OutboundMessage]) -> list[str]:
        if len(messages) == 0:
            return []

        topic_arn = self.topic_arn(topic_name=topic_name)
        message_ids: list[str] = []

        async with client("sns") as sns:
            for start in range(0, len(messages), PUBLISH_BATCH_LIMIT):
                batch = messages[start : start + PUBLISH_BATCH_LIMIT]
                response = await sns.publish_batch(TopicArn=topic_arn, PublishBatchRequestEntries=self.__entries(batch))

                failed = response.get("Failed", [])
                if len(failed) > 0:
                    raise InfrastructureError(
                        error_type=InfrastructureErrorType.CLOUD_ERROR,
                        message=f"SNS refused {len(failed)} of {len(batch)} messages for {topic_arn}: {failed}",
                    )

                published_by_id = {str(entry["Id"]): str(entry["MessageId"]) for entry in response["Successful"]}
                message_ids.extend(published_by_id[str(position)] for position in range(len(batch)))

        return message_ids

    def topic_arn(self, *, topic_name: str) -> str:
        configured = json.loads(os.getenv("EVENT_TOPIC_ARNS_JSON", "{}")).get(topic_name)
        if configured is not None:
            return str(configured)
        return f"arn:aws:sns:{get_region()}:{get_account_id()}:{scope_resource_name(topic_name)}"

    def __entries(self, messages: list[OutboundMessage], /) -> list[dict[str, Any]]:
        return [
            {
                "Id": str(position),
                "Message": base64.b64encode(message.get("data", "").encode()).decode(),
                "MessageAttributes": {
                    name: {"DataType": "String", "StringValue": value}
                    for name, value in message.get("attributes", {}).items()
                },
            }
            for position, message in enumerate(messages)
        ]


class SqsTaskQueue:
    def get_url(self, *, service: str, task: str, params: dict[str, str] | None = None) -> str:
        query = "" if params is None else f"?{urlencode(params)}"
        return f"https://{self.pool_host(service=service, task=task)}{COMMAND_PATH_PREFIX}/{task}{query}"

    def pool_host(self, *, service: str, task: str) -> str:
        pool = json.loads(os.getenv("EXECUTOR_POOLS_JSON", "{}")).get(f"{service}:{task}")
        sanitized_service = service.replace("_", "-")
        if pool is None:
            return f"{scope_resource_name(sanitized_service)}.{get_region()}.{POOL_HOST_SUFFIX}"
        sanitized_pool = str(pool).replace("_", "-")
        return f"{scope_resource_name(f'{sanitized_service}-p-{sanitized_pool}')}.{get_region()}.{POOL_HOST_SUFFIX}"

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
        payload = {
            "service": service,
            "task": task,
            "body": body,
            "params": params,
            "headers": headers,
            "scheduled_time": None if scheduled_time is None else scheduled_time.isoformat(),
        }

        async with client("sqs") as sqs:
            await sqs.send_message(
                QueueUrl=await self.queue_url(service=service, task=task),
                MessageBody=json.dumps(payload),
                DelaySeconds=self.delay_seconds(scheduled_time),
            )

    def delay_seconds(self, scheduled_time: datetime | None, /) -> int:
        if scheduled_time is None:
            return 0
        delay = int((scheduled_time - datetime.now(UTC)).total_seconds())
        return max(0, min(delay, MAXIMUM_DELAY_SECONDS))

    async def queue_url(self, *, service: str, task: str) -> str:
        configured = json.loads(os.getenv("SQS_EXECUTOR_QUEUES_JSON", "{}")).get(f"{service}:{task}")
        if configured is not None:
            return str(configured)

        async with client("sqs") as sqs:
            response = await sqs.get_queue_url(QueueName=self.queue_name(service=service, task=task))
        return str(response["QueueUrl"])

    def queue_name(self, *, service: str, task: str) -> str:
        return scope_resource_name(f"{service.replace('_', '-')}-c-{task.replace('_', '-')}")
