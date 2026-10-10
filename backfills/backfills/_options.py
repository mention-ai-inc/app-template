from __future__ import annotations

import asyncio
import os
from collections.abc import Coroutine
from typing import Annotated, Any

import typer

from control_plane.infrastructure.persistence.cache.base import aclose_cache_pool

ApplyOption = Annotated[bool, typer.Option("--apply", help="Write changes. Without this flag the run is a dry run.")]

OrganizationIdOption = Annotated[
    str | None, typer.Option("--organization-id", help="Limit to one organization (org_...).")
]


def feature_environment() -> str:
    return os.getenv("FEATURE_ENVIRONMENT", "")


def verb(apply: bool, *, done: str, pending: str) -> str:
    return done if apply else pending


def run_async[T](coroutine: Coroutine[Any, Any, T]) -> T:
    return asyncio.run(_run_with_cache_pool(coroutine))


async def _run_with_cache_pool[T](coroutine: Coroutine[Any, Any, T]) -> T:
    try:
        return await coroutine
    finally:
        await aclose_cache_pool()
