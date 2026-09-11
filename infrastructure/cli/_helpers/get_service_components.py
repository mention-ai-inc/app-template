import json
import os
from typing import TypedDict

import toml


class ServiceComponents(TypedDict):
    server: list[str]
    listener: list[str]
    executor: list[str]
    job: list[str]
    trigger: list[str]
    worker: list[str]


def get_service_components(*, service_name: str) -> ServiceComponents:
    service_components: ServiceComponents = {
        "server": [],
        "listener": [],
        "executor": [],
        "job": [],
        "trigger": [],
        "worker": [],
    }

    pyproject = toml.load(f"services/{service_name}/pyproject.toml")
    entrypoints = [script for script in pyproject["project"]["scripts"] if script.startswith("run-")]

    for entrypoint in entrypoints:
        _, component_type, *component_name_parts = entrypoint.split("-")
        component_name = "-".join(component_name_parts)
        service_components[component_type].append(component_name)

    return service_components


def main() -> None:
    components_by_service: dict[str, ServiceComponents] = {}
    services = os.listdir("services")
    for service in services:
        components_by_service[service] = get_service_components(service_name=service)

    print(json.dumps(components_by_service, indent=4))


if __name__ == "__main__":
    main()
