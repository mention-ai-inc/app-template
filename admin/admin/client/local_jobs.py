"""Teaching the local provider's job runner how to run admin's jobs.

On a cloud the runner starts a container that executes `admin <args>`. There is no container locally,
so admin hands the in-memory runner the same workers that image would have run. Without this the
local control plane could launch nothing, and `m admin -- backfill run` would only pretend.

A backfill's `run` is synchronous and drives its own event loop, so it goes to a thread rather than
being awaited — which is also closer to what it gets in production: an execution context of its own.
"""

from __future__ import annotations

import asyncio

from admin.backfill.registry import get
from admin.common.environment import feature_environment
from admin.seed.runner import run_seed
from admin.server.jobs import job_name
from library.providers.local.jobs import LocalJobRunner
from library.providers.registry import get_cloud_provider


def register_local_jobs() -> None:
    runner = get_cloud_provider().job_runner()
    if not isinstance(runner, LocalJobRunner):
        return
    runner.register(job_name=job_name("backfill"), handler=_run_backfill)
    runner.register(job_name=job_name("seed"), handler=_run_seed)


async def _run_backfill(args: list[str]) -> None:
    backfill = get(args[1])
    await asyncio.to_thread(
        backfill.run,
        environment=feature_environment(),
        apply="--apply" in args,
        organization_id=_option(args, "--organization-id"),
    )


async def _run_seed(args: list[str]) -> None:
    await run_seed(organization_id=_option(args, "--organization-id"))


def _option(args: list[str], name: str, /) -> str | None:
    if name not in args:
        return None
    return args[args.index(name) + 1]
