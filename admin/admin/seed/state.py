"""Persistence of what the seed provisioned, so re-runs reuse it instead of creating it again.

The organization the seed created (when no `--organization-id` was given) and its admin user are
written to `admin/data/seed/<env>.json` as soon as they exist, so a resumed run in the same working
tree targets the same organization. `admin/data` is gitignored and empty in a fresh admin image, so
a run from a new job container starts without state unless it is given an organization explicitly.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

GENERATED_DATA_DIR = Path("admin/data/seed")


@dataclass
class SeedState:
    organization_id: str | None = None
    admin_user_id: str | None = None


def state_path(feature_environment: str, /) -> Path:
    return GENERATED_DATA_DIR / f"{feature_environment}.json"


def load_state(feature_environment: str, /) -> SeedState:
    path = state_path(feature_environment)
    if not path.exists():
        return SeedState()
    return SeedState(**json.loads(path.read_text()))


def save_state(feature_environment: str, /, state: SeedState) -> None:
    path = state_path(feature_environment)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(state), indent=2))
