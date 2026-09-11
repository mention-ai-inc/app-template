import importlib
import json
import logging
import os
import sys

SERVICES = ["notes"]

combined_openapi = None

for service in SERVICES:
    sys.path.append(f"services/{service}")
    sys.path.append(f"services/{service}/.venv/lib/python3.13/site-packages")
    os.environ["SERVICE"] = service

    app = importlib.import_module(f"{service}_service.presentation.servers.rest.app").app

    from fastapi.openapi.utils import get_openapi

    service_openapi = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
    )

    if combined_openapi is None:
        combined_openapi = service_openapi
        combined_openapi["info"]["title"] = "Unified API"
        combined_openapi["info"]["description"] = "Combined API specification for all services"
    else:
        combined_openapi["paths"].update(service_openapi["paths"])
        if "components" in service_openapi:
            if "components" not in combined_openapi:
                combined_openapi["components"] = {}
            for component_type, components in service_openapi["components"].items():
                if component_type not in combined_openapi["components"]:
                    combined_openapi["components"][component_type] = {}
                combined_openapi["components"][component_type].update(components)

logging.info(f"Combined OpenAPI specification: {json.dumps(combined_openapi, indent=2)}")
print(json.dumps(combined_openapi, indent=2))
