import base64
import json
import logging
import os
from datetime import datetime
from typing import Any
from urllib.parse import urlencode

from library.infrastructure.cloud.base import AuthenticatedClient, raise_for_status
from library.infrastructure.cloud.constants import (
    COMMAND_PATH_PREFIX,
    FEATURE_PROJECT_ID,
    FEATURE_PROJECT_NUMBER,
    PRODUCTION_PROJECT_ID,
    PRODUCTION_PROJECT_NUMBER,
    REGION,
)
from library.infrastructure.cloud.project import get_project_id
from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType
from library.logs import SIMPLE_LOGGER_NAME

logger = logging.getLogger(SIMPLE_LOGGER_NAME)


class Tasks:
    BASE_URL = "https://cloudtasks.googleapis.com/v2beta3"

    def __init__(self, *, token: str | None = None) -> None:
        self.token = token
        self._client: AuthenticatedClient | None = None
        self._queue_name_cache: dict[str, str] = {}

    @property
    def client(self) -> AuthenticatedClient:
        if self._client is None:
            self._client = AuthenticatedClient(base_url=Tasks.BASE_URL, token=self.token)
        return self._client

    @property
    def project_number(self) -> str:
        project = get_project_id()
        project_number = {
            FEATURE_PROJECT_ID: FEATURE_PROJECT_NUMBER,
            PRODUCTION_PROJECT_ID: PRODUCTION_PROJECT_NUMBER,
        }.get(project)

        if project_number is None:
            raise InfrastructureError(
                error_type=InfrastructureErrorType.CLOUD_ERROR,
                message=f"Cloud Tasks could not determine project number for project: {project}",
            )

        return project_number

    def get_pool_name(self, *, service: str, task: str) -> str:
        pools_json = os.getenv("EXECUTOR_POOLS_JSON")
        if not pools_json:
            raise InfrastructureError(
                error_type=InfrastructureErrorType.CLOUD_ERROR,
                message="Cloud Tasks cannot route a command without EXECUTOR_POOLS_JSON",
            )

        pool_name = json.loads(pools_json).get(f"{service}:{task}")
        if pool_name is None:
            raise InfrastructureError(
                error_type=InfrastructureErrorType.CLOUD_ERROR,
                message=f"No executor pool is declared for service={service} task={task}",
            )

        return pool_name

    def get_base_url(self, *, service: str, pool: str) -> str:
        sanitized_service = service.replace("_", "-")
        sanitized_pool = pool.replace("_", "-")
        return f"https://{os.getenv('FEATURE_ENVIRONMENT', '')}{sanitized_service}-p-{sanitized_pool}-{self.project_number}.{REGION}.run.app"

    def get_url(self, *, service: str, task: str, params: dict[str, str] | None = None) -> str:
        base_url = self.get_base_url(service=service, pool=self.get_pool_name(service=service, task=task))
        url_params = "?" + urlencode(params) if params is not None else ""
        return f"{base_url}{COMMAND_PATH_PREFIX}/{task}{url_params}"

    async def get_queue_name(self, *, service: str, task: str) -> str:
        cache_key = f"{service}:{task}"
        if cache_key in self._queue_name_cache:
            return self._queue_name_cache[cache_key]

        queues_json = os.getenv("CLOUD_TASKS_QUEUES_JSON")
        if queues_json:
            queues_map = json.loads(queues_json)
            if queue_name := queues_map.get(cache_key):
                self._queue_name_cache[cache_key] = queue_name
                return queue_name

        queues_response = await self.client.get(f"/projects/{get_project_id()}/locations/{REGION}/queues")
        queues_response.raise_for_status()
        queues = queues_response.json()["queues"]
        queue_name = next(
            (
                queue["name"].split("/")[-1]
                for queue in queues
                if queue["name"].startswith(
                    f"projects/{get_project_id()}/locations/{REGION}/queues/{os.getenv('FEATURE_ENVIRONMENT', '')}{service.replace('_', '-')}-{task.replace('_', '-')}"
                )
            ),
            None,
        )
        if queue_name is None:
            raise ValueError(f"Queue not found for service={service} task={task}")

        self._queue_name_cache[cache_key] = queue_name
        return queue_name

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
        base_url = self.get_base_url(service=service, pool=self.get_pool_name(service=service, task=task))
        url_params = "?" + urlencode(params) if params is not None else ""
        url = f"{base_url}{COMMAND_PATH_PREFIX}/{task}{url_params}"
        email = f"{os.getenv('FEATURE_ENVIRONMENT', '')}{service}-s@{get_project_id()}.iam.gserviceaccount.com"
        task_definition: dict[str, Any] = {
            "httpRequest": {
                "httpMethod": "POST",
                "url": url,
                "body": base64.b64encode(json.dumps(body, default=str).encode()).decode(),
                "oidcToken": {"serviceAccountEmail": email, "audience": base_url},
                "headers": {"Content-Type": "application/json"},
            }
        }

        if scheduled_time is not None:
            task_definition["scheduleTime"] = scheduled_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        if headers is not None:
            task_definition["httpRequest"]["headers"].update(headers)

        queue_name = await self.get_queue_name(service=service, task=task)
        response = await self.client.post(
            f"/projects/{get_project_id()}/locations/{REGION}/queues/{queue_name}/tasks", json={"task": task_definition}
        )

        if response.status_code == 404:
            logger.error(f"Target URL not found for task: {url}")

        raise_for_status(response)
