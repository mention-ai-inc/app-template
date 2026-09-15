import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime

from library.application.ports.jobs import JobDefinition, JobExecution, JobStatus
from library.application.ports.logs import DEFAULT_LOG_LINE_LIMIT, LogLine
from library.infrastructure.control_plane import JobExecutionNotFoundError, JobNotFoundError
from library.logs import SIMPLE_LOGGER_NAME

type JobHandler = Callable[[list[str]], Awaitable[None]]

logger = logging.getLogger(SIMPLE_LOGGER_NAME)


@dataclass
class LocalExecution:
    execution_id: str
    job_name: str
    args: list[str]
    status: JobStatus = "pending"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    lines: list[LogLine] = field(default_factory=list[LogLine])


_current_execution: ContextVar[LocalExecution | None] = ContextVar("local_job_execution", default=None)
_capturing = False


class ExecutionLogHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        execution = _current_execution.get()
        if execution is None:
            return
        execution.lines.append(
            LogLine(
                timestamp=datetime.fromtimestamp(record.created, UTC),
                message=record.getMessage(),
                severity=record.levelname,
            )
        )


@dataclass
class LocalJobRunner:
    handlers: dict[str, JobHandler] = field(default_factory=dict[str, JobHandler])
    images: dict[str, str] = field(default_factory=dict[str, str])
    executions: dict[str, LocalExecution] = field(default_factory=dict[str, LocalExecution])
    running: set[asyncio.Task[None]] = field(default_factory=set[asyncio.Task[None]])

    def register(self, *, job_name: str, handler: JobHandler, image: str | None = None) -> None:
        self.handlers[job_name] = handler
        if image is not None:
            self.images[job_name] = image

    async def run_job(self, *, job_name: str, args: list[str]) -> str:
        handler = self.handlers.get(job_name)
        if handler is None:
            raise JobNotFoundError(job_name)

        _start_capturing()
        execution = LocalExecution(
            execution_id=f"{job_name}-{uuid.uuid4().hex[:8]}", job_name=job_name, args=list(args)
        )
        self.executions[execution.execution_id] = execution
        task = asyncio.create_task(self.__execute(execution, handler))
        self.running.add(task)
        task.add_done_callback(self.running.discard)
        return execution.execution_id

    async def get_job(self, *, job_name: str) -> JobDefinition:
        if job_name not in self.handlers:
            raise JobNotFoundError(job_name)
        return JobDefinition(job_name=job_name, image=self.images.get(job_name))

    async def get_execution(self, *, job_name: str, execution_id: str) -> JobExecution:  # noqa: ARG002
        execution = self.executions.get(execution_id)
        if execution is None:
            raise JobExecutionNotFoundError(execution_id)
        return JobExecution(
            execution_id=execution.execution_id,
            job_name=execution.job_name,
            status=execution.status,
            args=list(execution.args),
            created_at=execution.created_at,
            started_at=execution.started_at,
            completed_at=execution.completed_at,
            succeeded_count=1 if execution.status == "succeeded" else 0,
            failed_count=1 if execution.status == "failed" else 0,
        )

    def clear(self) -> None:
        self.executions.clear()
        self.running.clear()

    async def __execute(self, execution: LocalExecution, handler: JobHandler) -> None:
        token = _current_execution.set(execution)
        execution.status = "running"
        execution.started_at = datetime.now(UTC)
        try:
            await handler(execution.args)
            execution.status = "succeeded"
        except Exception:
            logger.exception("Job %s failed", execution.job_name)
            execution.status = "failed"
        finally:
            execution.completed_at = datetime.now(UTC)
            _current_execution.reset(token)


@dataclass
class LocalLogReader:
    runner: LocalJobRunner

    async def read_execution_logs(
        self,
        *,
        job_name: str,  # noqa: ARG002
        execution_id: str,
        limit: int = DEFAULT_LOG_LINE_LIMIT,
    ) -> list[LogLine]:
        execution = self.runner.executions.get(execution_id)
        if execution is None:
            raise JobExecutionNotFoundError(execution_id)
        return list(execution.lines[:limit])


def _start_capturing() -> None:
    global _capturing
    if _capturing:
        return
    logging.getLogger(SIMPLE_LOGGER_NAME).addHandler(ExecutionLogHandler())
    _capturing = True
