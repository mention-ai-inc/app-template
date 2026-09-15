"""Feature-environment resolution shared by every admin command.

`FEATURE_ENVIRONMENT` is set by the `m` wrapper (from the flag or the current branch). An empty value
means the production slot. Commands that must never touch production call `require_feature_environment`;
backfills that legitimately target production read `feature_environment` directly.

The default seed organization comes from the `FEATURE_ENVIRONMENT_SEED_ORGANIZATION_ID` environment
variable — set locally in the shell and injected in CI from the GitHub Actions variable of the same
name. When it is unset the seed creates an organization of its own.
"""

from __future__ import annotations

import os

SEED_ORGANIZATION_VARIABLE = "FEATURE_ENVIRONMENT_SEED_ORGANIZATION_ID"


def feature_environment() -> str:
    return os.getenv("FEATURE_ENVIRONMENT", "")


def require_feature_environment() -> str:
    environment = feature_environment()
    if not environment:
        raise SystemExit("FEATURE_ENVIRONMENT is empty (production). This command targets a feature environment only.")
    return environment


def default_seed_organization_id() -> str | None:
    return os.getenv(SEED_ORGANIZATION_VARIABLE) or None
