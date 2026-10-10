from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Callable
from dataclasses import dataclass

from backfills import migrations


@dataclass(frozen=True)
class Backfill:
    name: str
    description: str
    run: Callable[..., None]


def discover() -> list[Backfill]:
    found: list[tuple[str, Backfill]] = []
    for module_info in pkgutil.iter_modules(migrations.__path__):
        module = importlib.import_module(f"{migrations.__name__}.{module_info.name}")
        backfill = getattr(module, "BACKFILL", None)
        if isinstance(backfill, Backfill):
            found.append((module_info.name, backfill))
    return [backfill for _, backfill in sorted(found, key=lambda item: item[0])]


def get(name: str) -> Backfill:
    backfills = discover()
    for backfill in backfills:
        if backfill.name == name:
            return backfill
    available = ", ".join(backfill.name for backfill in backfills) or "(none)"
    raise SystemExit(f"Unknown backfill '{name}'. Available: {available}")
