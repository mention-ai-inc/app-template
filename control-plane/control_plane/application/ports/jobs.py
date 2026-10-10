from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

type JobStatus = Literal["pending", "running", "succeeded", "failed"]


@dataclass(frozen=True)
class JobExecution:
    execution_id: str
    job_name: str
    status: JobStatus
    args: list[str]
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    task_count: int = 1
    succeeded_count: int = 0
    failed_count: int = 0


@dataclass(frozen=True)
class JobDefinition:
    job_name: str
    image: str | None = None


class IJobRunner(Protocol):
    async def run_job(self, *, job_name: str, args: list[str]) -> str: ...

    async def get_job(self, *, job_name: str) -> JobDefinition: ...

    async def get_execution(self, *, job_name: str, execution_id: str) -> JobExecution: ...
