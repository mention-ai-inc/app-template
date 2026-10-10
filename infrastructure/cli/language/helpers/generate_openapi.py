import importlib
import json
import os
import sys
from pathlib import Path
from typing import Any, cast

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

SERVICES_ROOT = Path("services")


def service_names() -> list[str]:
    return sorted(manifest.parent.name for manifest in SERVICES_ROOT.glob("*/pyproject.toml"))


def service_openapi(*, service: str) -> dict[str, Any]:
    os.environ["SERVICE"] = service
    app = cast(FastAPI, importlib.import_module(f"{service}_service.presentation.servers.rest.app").app)
    return get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
    )


def merge(*, combined: dict[str, Any], service_spec: dict[str, Any]) -> None:
    combined["paths"].update(service_spec["paths"])
    components = cast(dict[str, dict[str, Any]], service_spec.get("components", {}))
    for component_type, entries in components.items():
        combined.setdefault("components", {}).setdefault(component_type, {}).update(entries)


def main() -> None:
    specs = [service_openapi(service=service) for service in service_names()]
    if not specs:
        print("No services found under services/", file=sys.stderr)
        sys.exit(1)

    combined = specs[0]
    combined["info"]["title"] = "Unified API"
    combined["info"]["description"] = "Combined API specification for all services"
    for service_spec in specs[1:]:
        merge(combined=combined, service_spec=service_spec)

    print(json.dumps(combined, indent=2))


if __name__ == "__main__":
    main()
