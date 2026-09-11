"""Shared Typer option shapes and helpers.

Every admin command defaults to a dry run and takes `--apply` to write. `verb` renders the past /
conditional tense pair used in progress output, and `run_async` lets a sync Typer command drive an
async worker.
"""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Annotated, Any

import typer

from library.infrastructure.persistence.cache.base import aclose_cache_pool

ApplyOption = Annotated[bool, typer.Option("--apply", help="Write changes. Without this flag the run is a dry run.")]

OrganizationIdOption = Annotated[str, typer.Option("--organization-id", help="Clerk organization id (org_...).")]


def verb(apply: bool, *, done: str, pending: str) -> str:
    return done if apply else pending


def run_async[T](coroutine: Coroutine[Any, Any, T]) -> T:
    return asyncio.run(_run_with_cache_pool(coroutine))


async def _run_with_cache_pool[T](coroutine: Coroutine[Any, Any, T]) -> T:
    try:
        return await coroutine
    finally:
        await aclose_cache_pool()
