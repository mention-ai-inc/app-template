from datetime import datetime

from pydantic import BaseModel, Field

from library.infrastructure.cloud.base import AuthenticatedClient, raise_for_status
from library.infrastructure.cloud.constants import REGION
from library.infrastructure.cloud.project import get_project_id


class ExecutionContainer(BaseModel):
    image: str
    args: list[str] = Field(default_factory=list)


class ExecutionTemplate(BaseModel):
    containers: list[ExecutionContainer] = Field(default_factory=list)


class Execution(BaseModel):
    name: str
    create_time: datetime | None = Field(default=None, validation_alias="createTime")
    start_time: datetime | None = Field(default=None, validation_alias="startTime")
    completion_time: datetime | None = Field(default=None, validation_alias="completionTime")
    task_count: int = Field(default=0, validation_alias="taskCount")
    running_count: int = Field(default=0, validation_alias="runningCount")
    succeeded_count: int = Field(default=0, validation_alias="succeededCount")
    failed_count: int = Field(default=0, validation_alias="failedCount")
    cancelled_count: int = Field(default=0, validation_alias="cancelledCount")
    template: ExecutionTemplate = Field(default_factory=ExecutionTemplate)

    @property
    def short_name(self) -> str:
        return self.name.rsplit("/", 1)[-1]

    @property
    def status(self) -> str:
        if self.completion_time is None:
            return "running" if self.running_count else "pending"
        if self.failed_count or self.cancelled_count:
            return "failed"
        return "succeeded"

    @property
    def args(self) -> list[str]:
        return self.template.containers[0].args if self.template.containers else []


class JobContainer(BaseModel):
    image: str


class JobTaskTemplate(BaseModel):
    containers: list[JobContainer] = Field(default_factory=list)


class JobTemplate(BaseModel):
    template: JobTaskTemplate = Field(default_factory=JobTaskTemplate)


class Job(BaseModel):
    name: str
    template: JobTemplate = Field(default_factory=JobTemplate)

    @property
    def image(self) -> str | None:
        containers = self.template.template.containers
        return containers[0].image if containers else None


class CloudRun:
    BASE_URL = "https://run.googleapis.com/v2"

    def __init__(self, *, project: str | None = None, region: str = REGION, token: str | None = None) -> None:
        self.project = project or get_project_id()
        self.region = region
        self.token = token
        self._client: AuthenticatedClient | None = None

    @property
    def client(self) -> AuthenticatedClient:
        if self._client is None:
            self._client = AuthenticatedClient(base_url=CloudRun.BASE_URL, token=self.token)
        return self._client

    async def run_job(self, *, job_name: str, args: list[str]) -> str:
        response = await self.client.post(
            f"/{self.__job_path(job_name)}:run",
            json={"overrides": {"containerOverrides": [{"args": args}]}},
        )
        raise_for_status(response)
        execution_name: str = response.json()["metadata"]["name"]
        return execution_name.rsplit("/", 1)[-1]

    async def get_job(self, *, job_name: str) -> Job:
        response = await self.client.get(f"/{self.__job_path(job_name)}")
        raise_for_status(response)
        return Job.model_validate(response.json())

    async def get_execution(self, *, job_name: str, execution_name: str) -> Execution:
        response = await self.client.get(f"/{self.__job_path(job_name)}/executions/{execution_name}")
        raise_for_status(response)
        return Execution.model_validate(response.json())

    def __job_path(self, job_name: str) -> str:
        return f"projects/{self.project}/locations/{self.region}/jobs/{job_name}"
