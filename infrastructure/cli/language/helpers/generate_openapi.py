import importlib
import json
import os
import sys
from pathlib import Path
from typing import Any, cast

from fastapi import FastAPI
from fastapi.routing import APIRoute

SERVICES_ROOT = Path("services")


def service_names() -> list[str]:
    return sorted(manifest.parent.name for manifest in SERVICES_ROOT.glob("*/pyproject.toml"))


def service_app(*, service: str) -> FastAPI:
    os.environ["SERVICE"] = service
    return cast(FastAPI, importlib.import_module(f"{service}_service.presentation.servers.rest.app").app)


def unpinned_routes(app: FastAPI) -> list[str]:
    problems: list[str] = []
    for route in app.routes:
        if not isinstance(route, APIRoute) or not route.include_in_schema:
            continue
        if route.summary is None:
            problems.append(f"{route.path} ({route.name}) has no explicit summary")
        if not route.tags:
            problems.append(f"{route.path} ({route.name}) has no tags")
    return problems


def merge(*, combined: dict[str, Any], service_spec: dict[str, Any]) -> None:
    combined["paths"].update(service_spec["paths"])
    components = cast(dict[str, dict[str, Any]], service_spec.get("components", {}))
    for component_type, entries in components.items():
        combined.setdefault("components", {}).setdefault(component_type, {}).update(entries)


def main() -> None:
    apps = [service_app(service=service) for service in service_names()]
    if not apps:
        print("No services found under services/", file=sys.stderr)
        sys.exit(1)

    problems = [problem for app in apps for problem in unpinned_routes(app)]
    if problems:
        print("Every REST route needs an explicit summary and tags:", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        sys.exit(1)

    specs = [app.openapi() for app in apps]
    combined = specs[0]
    combined["info"]["title"] = "Unified API"
    combined["info"]["description"] = "Combined API specification for all services"
    for service_spec in specs[1:]:
        merge(combined=combined, service_spec=service_spec)

    print(json.dumps(combined, indent=2))


if __name__ == "__main__":
    main()
