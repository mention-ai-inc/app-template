"""Teaching the local provider's job runner how to run admin's jobs.

On a cloud the runner starts a container: the `backfills` image with `backfill <args>`, or the admin
image with `admin seed <args>`. There is no container locally, so admin hands the in-memory runner
the same workers those images would have run. Without this the local control plane could launch
nothing, and `m admin -- backfill run` would only pretend.

The backfill job is a subprocess of whatever `BACKFILL_COMMAND` names (`backfill` on `PATH` by
default), with its output streamed into the execution's log lines exactly as a cloud log reader
would return them. With no language slot installed there is no such command: listing then reports an
empty catalogue with a clear message, and running fails.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shlex

from admin.common.environment import feature_environment
from admin.seed.runner import run_seed
from admin.server.jobs import job_name
from control_plane.logs import SIMPLE_LOGGER_NAME
from control_plane.providers.local.jobs import LocalJobRunner
from control_plane.providers.registry import get_cloud_provider

BACKFILL_COMMAND_VARIABLE = "BACKFILL_COMMAND"
DEFAULT_BACKFILL_COMMAND = "backfill"
EMPTY_CATALOGUE = json.dumps({"backfills": []})

logger = logging.getLogger(SIMPLE_LOGGER_NAME)


class BackfillCommandFailed(Exception):
    def __init__(self, *, command: str, returncode: int) -> None:
        super().__init__(f"{command} exited with status {returncode}")


def register_local_jobs() -> None:
    runner = get_cloud_provider().job_runner()
    if not isinstance(runner, LocalJobRunner):
        return
    runner.register(job_name=job_name("backfill"), handler=_run_backfill)
    runner.register(job_name=job_name("seed"), handler=_run_seed)


def backfill_command() -> list[str]:
    return shlex.split(os.getenv(BACKFILL_COMMAND_VARIABLE, DEFAULT_BACKFILL_COMMAND))


async def _run_backfill(args: list[str]) -> None:
    command = [*backfill_command(), *args]
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env={**os.environ, "FEATURE_ENVIRONMENT": feature_environment()},
        )
    except FileNotFoundError:
        logger.warning(
            "No backfill command at %r. Install the language slot's backfills package or set %s.",
            command[0],
            BACKFILL_COMMAND_VARIABLE,
        )
        if args[:1] == ["list"]:
            logger.info(EMPTY_CATALOGUE)
            return
        raise

    if process.stdout is not None:
        async for raw_line in process.stdout:
            logger.info(raw_line.decode(errors="replace").rstrip())

    returncode = await process.wait()
    if returncode != 0:
        raise BackfillCommandFailed(command=command[0], returncode=returncode)


async def _run_seed(args: list[str]) -> None:
    await run_seed(organization_id=_option(args, "--organization-id"))


def _option(args: list[str], name: str, /) -> str | None:
    if name not in args:
        return None
    return args[args.index(name) + 1]
