from datetime import datetime
from typing import Any, Protocol


class ITaskQueue(Protocol):
    def get_url(self, *, service: str, task: str, params: dict[str, str] | None = None) -> str: ...

    async def add_task(
        self,
        *,
        service: str,
        task: str,
        body: dict[str, Any],
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        scheduled_time: datetime | None = None,
    ) -> None: ...
