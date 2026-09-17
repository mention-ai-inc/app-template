from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from mention_template.setup import configuration


def plan(config: dict[str, Any], event_name: str, event: dict[str, Any]) -> dict[str, str]:
    merged = event_name == "pull_request" and event.get("pull_request", {}).get("merged") is True
    manual = event_name == "workflow_dispatch"
    inputs: dict[str, Any] = event.get("inputs") or {}
    target = "demo" if merged else inputs.get("environment", "production")
    if target not in ("demo", "production"):
        raise ValueError("Select demo or production")

    def selected(name: str) -> bool:
        value = inputs.get(name, False)
        if type(value) is bool:
            return value
        if value in ("true", "false"):
            return value == "true"
        raise ValueError("Deployment selections must be booleans")

    enabled = manual or (merged and config.get("deployment", {"auto_demo": True})["auto_demo"])
    selections = {
        surface: enabled and config["surfaces"][surface] and (merged or selected(surface))
        for surface in ("web", "mcp", "admin")
    }
    notes = enabled and (merged or selected("notes"))
    operations = enabled and manual and selected("terraform_operations")
    full_demo = (
        enabled
        and target == "demo"
        and notes
        and all(not config["surfaces"][surface] or selections[surface] for surface in selections)
    )
    result = {
        "enabled": enabled,
        "merged": merged,
        "notes": notes,
        "terraform_operations": operations,
        "full_demo": full_demo,
        **selections,
    }
    return {"target": target, **{key: str(value).lower() for key, value in result.items()}}


def main(root: Path) -> None:
    config = (
        configuration(root)
        if (root / "project.json").exists()
        else {"surfaces": dict.fromkeys(("web", "mcp", "admin"), True), "deployment": {"auto_demo": True}}
    )
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())
    for key, value in plan(config, os.environ["GITHUB_EVENT_NAME"], event).items():
        print(f"{key}={value}")
