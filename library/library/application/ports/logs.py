from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

DEFAULT_LOG_LINE_LIMIT = 1000


@dataclass(frozen=True)
class LogLine:
    timestamp: datetime
    message: str
    severity: str | None = None


class ILogReader(Protocol):
    async def read_execution_logs(
        self, *, job_name: str, execution_id: str, limit: int = DEFAULT_LOG_LINE_LIMIT
    ) -> list[LogLine]: ...
