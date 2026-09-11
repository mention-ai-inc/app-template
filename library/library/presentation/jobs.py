import asyncio
import json
import logging
import os
from collections.abc import Callable, Coroutine
from typing import Any

from library.application.audit.context import flush_audit_context, init_audit_context, set_source
from library.domain.audit.event import AuditSource
from library.infrastructure.audit.snapshot import flush_snapshot_context, init_snapshot_context
from library.infrastructure.persistence.cache.base import aclose_cache_pool
from library.logs import SIMPLE_LOGGER_NAME, flush_log_context, init_log_context
from library.presentation.api.environment import ComponentType

logger = logging.getLogger(SIMPLE_LOGGER_NAME)


def run_job(job: Callable[[], Coroutine[Any, Any, None]], /) -> None:
    log_context_token = init_log_context()
    audit_context_token = init_audit_context()
    snapshot_context_token = init_snapshot_context()
    set_source(AuditSource.JOB)
    try:
        asyncio.run(__run_with_cache_pool(job))
    finally:
        flush_audit_context(token=audit_context_token)
        flush_snapshot_context(token=snapshot_context_token)
        context = flush_log_context(token=log_context_token)
        log: dict[str, Any] = {
            "logType": "custom",
            "severity": "INFO",
            "service": os.getenv("SERVICE", ""),
            "component_type": ComponentType(os.getenv("COMPONENT_TYPE", "")),
            "component_name": os.getenv("COMPONENT_NAME", ""),
            "context": context,
        }
        logger.info(json.dumps(log, default=str))


async def __run_with_cache_pool(job: Callable[[], Coroutine[Any, Any, None]], /) -> None:
    try:
        await job()
    finally:
        await aclose_cache_pool()
