import os
import re

import sentry_sdk
from sentry_sdk.integrations.logging import ignore_logger

from library.logs import SIMPLE_LOGGER_NAME

SENTRY_IGNORED_LOGGERS = [SIMPLE_LOGGER_NAME, "gunicorn.error", "weaviate-client"]

# High-cardinality tokens that vary per event and would otherwise split one logical error into many issues
HIGH_CARDINALITY_TOKEN = re.compile(
    r"""
      [0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}  # uuids
    | '[^']*' | "[^"]*"                                              # quoted literals
    | \b0x[0-9a-f]+\b                                                # hex
    | \b\d+\b                                                        # bare numbers
    """,
    re.IGNORECASE | re.VERBOSE,
)


def normalize_error_message(message: str) -> str:
    """Replace high-cardinality tokens with a placeholder so equivalent errors share a fingerprint."""
    return HIGH_CARDINALITY_TOKEN.sub("·", message).strip()


def init_sentry() -> None:
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN", ""),
        send_default_pii=True,
        auto_enabling_integrations=False,
        environment=os.getenv("FEATURE_ENVIRONMENT") or "production",
    )
    for logger_name in SENTRY_IGNORED_LOGGERS:
        ignore_logger(logger_name)
