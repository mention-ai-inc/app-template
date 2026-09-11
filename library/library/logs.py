import logging.config
import os
import warnings
from contextvars import ContextVar, Token
from typing import Any

import logfire

warnings.filterwarnings("ignore", category=DeprecationWarning)

SIMPLE_LOGGER_NAME = "simple"
DETAILED_LOGGER_NAME = "detailed"

_log_context: ContextVar[dict[str, Any]] = ContextVar("log_context", default={})


def init_log_context() -> Token[dict[str, Any]]:
    """Start a fresh request-scoped context. Call once at the beginning of each HTTP request or job."""
    return _log_context.set({})


def add_log_context(**kwargs: Any) -> None:
    """Merge keyword fields into the current request-scoped log context.

    Duplicate keys overwrite earlier values. Do not call with the same key inside loops.
    See `.cursor/rules/logging.mdc` for conventions on what to log.
    """
    _log_context.get().update(kwargs)


def flush_log_context(*, token: Token[dict[str, Any]]) -> dict[str, Any]:
    """Return accumulated context and reset to the state before ``init_log_context``."""
    data = dict(_log_context.get())
    _log_context.reset(token)
    return data


logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": True,
        "loggers": {
            "": {
                "handlers": ["stderr"],
                "level": "WARNING",
                "propagate": False,
            },
            "uvicorn.error": {
                "handlers": ["null"],
                "level": "CRITICAL",
                "propagate": False,
            },
            "uvicorn": {
                "handlers": ["null"],
                "level": "CRITICAL",
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["null"],
                "level": "CRITICAL",
                "propagate": False,
            },
            "gunicorn.error": {
                "handlers": ["null"],
                "level": "CRITICAL",
                "propagate": False,
            },
            "gunicorn": {
                "handlers": ["null"],
                "level": "CRITICAL",
                "propagate": False,
            },
            "gunicorn.access": {
                "handlers": ["null"],
                "level": "CRITICAL",
                "propagate": False,
            },
            "py.warnings": {
                "handlers": ["null"],
                "level": "CRITICAL",
                "propagate": False,
            },
            SIMPLE_LOGGER_NAME: {
                "handlers": ["stderr_json"],
                "level": "DEBUG",
                "propagate": False,
            },
            DETAILED_LOGGER_NAME: {
                "handlers": ["stderr_detailed"],
                "level": "DEBUG",
                "propagate": False,
            },
        },
        "handlers": {
            "null": {
                "class": "logging.NullHandler",
            },
            "stderr_detailed": {
                "class": "logging.StreamHandler",
                "formatter": "detailed",
                "level": "DEBUG",
                "stream": "ext://sys.stderr",
            },
            "stderr_debug": {
                "class": "logging.StreamHandler",
                "formatter": "detailed",
                "level": "DEBUG",
                "stream": "ext://sys.stderr",
            },
            "stderr_json": {
                "class": "logging.StreamHandler",
                "formatter": "json",
                "level": "DEBUG",
                "stream": "ext://sys.stderr",
            },
            "stderr": {
                "class": "logging.StreamHandler",
                "formatter": "json",
                "level": "DEBUG",
                "stream": "ext://sys.stderr",
            },
        },
        "formatters": {
            "detailed": {
                "format": "[%(name)s] %(levelname)s --- %(asctime)s --- %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "json": {"format": "%(message)s", "datefmt": "%Y-%m-%d %H:%M:%S"},
        },
    }
)

logfire.configure(
    send_to_logfire="if-token-present",
    token=os.getenv("LOGFIRE_WRITE_TOKEN"),
    service_name=os.getenv("SERVICE") or None,
    environment=os.getenv("FEATURE_ENVIRONMENT") or None,
    console=False,
)
logfire.instrument_pydantic_ai()
