import json
import tomllib
from pathlib import Path
from typing import TypedDict

SERVICES_ROOT = Path("services")


class ServiceComponents(TypedDict):
    server: list[str]
    pool: list[str]
    job: list[str]
    worker: list[str]


def get_service_components(*, manifest: Path) -> ServiceComponents:
    service_components: ServiceComponents = {
        "server": [],
        "pool": [],
        "job": [],
        "worker": [],
    }

    with manifest.open("rb") as handle:
        pyproject = tomllib.load(handle)
    entrypoints = [script for script in pyproject["project"]["scripts"] if script.startswith("run-")]

    for entrypoint in entrypoints:
        _, component_type, *component_name_parts = entrypoint.split("-")
        component_name = "-".join(component_name_parts)
        service_components[component_type].append(component_name)

    return service_components


def main() -> None:
    components_by_service = {
        manifest.parent.name: get_service_components(manifest=manifest)
        for manifest in sorted(SERVICES_ROOT.glob("*/pyproject.toml"))
    }
    print(json.dumps(components_by_service, indent=4))


if __name__ == "__main__":
    main()
