"""The deployed backfill catalogue, read from the backfill job itself.

Admin does not know which backfills exist: they live in the language slot's `backfills` image, not in
admin's. Listing them means launching `{env}admin-j-backfill` with `list --json`, waiting for it to
finish, and reading the one catalogue line it logs. A job launch per request would be slow and noisy,
so the answer is cached per job name for a few minutes; a backfill only appears once its image is
deployed anyway.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from admin.server.jobs import JobLauncher, job_name
from control_plane.application.errors import ApplicationError, ApplicationErrorType
from control_plane.application.ports.jobs import JobExecution
from control_plane.application.ports.logs import ILogReader

BACKFILL_GROUP = "backfill"
LIST_ARGS = ["list", "--json"]
CATALOGUE_LINE_PREFIX = '{"backfills"'
CACHE_TTL = timedelta(minutes=5)
TERMINAL_STATUSES = ("succeeded", "failed")
DEFAULT_POLL_INTERVAL_SECONDS = 2.0
LOG_READ_ATTEMPTS = 5


@dataclass(frozen=True)
class BackfillEntry:
    name: str
    description: str


@dataclass(frozen=True)
class CachedCatalogue:
    entries: list[BackfillEntry]
    expires_at: datetime


_cache: dict[str, CachedCatalogue] = {}


def reset_catalogue_cache() -> None:
    _cache.clear()


def parse_catalogue(messages: Iterable[str], /) -> list[BackfillEntry] | None:
    for message in messages:
        line = message.strip()
        if not line.startswith(CATALOGUE_LINE_PREFIX):
            continue
        try:
            catalogue = json.loads(line)
            return [
                BackfillEntry(name=entry["name"], description=entry["description"]) for entry in catalogue["backfills"]
            ]
        except (ValueError, KeyError, TypeError) as error:
            raise ApplicationError(
                error_type=ApplicationErrorType.PROCESS_FAILED,
                message=f"The backfill job reported a malformed catalogue: {line}",
            ) from error
    return None


class BackfillCatalogue:
    def __init__(
        self,
        *,
        launcher: JobLauncher,
        log_reader: ILogReader,
        poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
    ) -> None:
        self._launcher = launcher
        self._log_reader = log_reader
        self._poll_interval_seconds = poll_interval_seconds

    async def list(self) -> list[BackfillEntry]:
        key = job_name(BACKFILL_GROUP)
        now = datetime.now(UTC)
        cached = _cache.get(key)
        if cached is not None and cached.expires_at > now:
            return list(cached.entries)

        entries = await self.__discover()
        _cache[key] = CachedCatalogue(entries=entries, expires_at=now + CACHE_TTL)
        return list(entries)

    async def has(self, name: str, /) -> bool:
        return any(entry.name == name for entry in await self.list())

    async def __discover(self) -> list[BackfillEntry]:
        execution_id = await self._launcher.launch(group=BACKFILL_GROUP, args=LIST_ARGS)
        execution = await self.__wait(execution_id)
        for attempt in range(LOG_READ_ATTEMPTS):
            lines = await self._log_reader.read_execution_logs(job_name=execution.job_name, execution_id=execution_id)
            entries = parse_catalogue(line.message for line in lines)
            if entries is not None:
                return entries
            if attempt + 1 < LOG_READ_ATTEMPTS:
                await asyncio.sleep(self._poll_interval_seconds)
        raise ApplicationError(
            error_type=ApplicationErrorType.PROCESS_FAILED,
            message=f"Execution {execution_id} ({execution.status}) reported no backfill catalogue; see its logs.",
        )

    async def __wait(self, execution_id: str) -> JobExecution:
        while True:
            execution = await self._launcher.execution(execution_id=execution_id)
            if execution.status in TERMINAL_STATUSES:
                return execution
            await asyncio.sleep(self._poll_interval_seconds)
