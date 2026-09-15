import json
import os
from typing import Any

from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType

DEFAULT_REGION = "eastus"
COSMOS_ENDPOINT = "COSMOS_ENDPOINT"
COSMOS_DATABASE = "COSMOS_DATABASE"
COSMOS_KEY = "COSMOS_KEY"
COSMOS_TLS_VERIFY = "COSMOS_TLS_VERIFY"
BLOB_ACCOUNT_KEY = "BLOB_ACCOUNT_KEY"
SERVICE_BUS_NAMESPACE = "SERVICE_BUS_NAMESPACE"
SERVICE_BUS_QUEUES_JSON = "SERVICE_BUS_QUEUES_JSON"
SERVICE_BUS_SUBSCRIPTIONS_JSON = "SERVICE_BUS_SUBSCRIPTIONS_JSON"
CHANGE_FEED_TRIGGERS_JSON = "CHANGE_FEED_TRIGGERS_JSON"
BLOB_ACCOUNT_URL = "BLOB_ACCOUNT_URL"
KEY_VAULT_URI = "AZURE_KEY_VAULT_URI"
SUBSCRIPTION_ID = "AZURE_SUBSCRIPTION_ID"
RESOURCE_GROUP = "AZURE_RESOURCE_GROUP"
REGION = "AZURE_REGION"


def feature_environment() -> str:
    return os.getenv("FEATURE_ENVIRONMENT", "")


def scoped(resource_name: str, /) -> str:
    return feature_environment() + resource_name


def required(variable: str, /) -> str:
    value = os.getenv(variable)
    if not value:
        raise InfrastructureError(
            error_type=InfrastructureErrorType.ENVIRONMENT_ERROR,
            message=f"{variable} is not set, so the Azure provider cannot reach that resource",
        )
    return value


def routing_table(variable: str, /) -> dict[str, Any]:
    raw = os.getenv(variable)
    if not raw:
        raise InfrastructureError(
            error_type=InfrastructureErrorType.ENVIRONMENT_ERROR,
            message=f"{variable} is not set, so the Azure provider cannot route to that resource",
        )

    try:
        table: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as error:
        raise InfrastructureError(
            error_type=InfrastructureErrorType.ENVIRONMENT_ERROR,
            message=f"{variable} is not valid JSON: {error}",
        ) from error

    return table


def route_key(*, service: str, name: str) -> str:
    return f"{service}:{name}"


def tls_verification_enabled() -> bool:
    return os.getenv(COSMOS_TLS_VERIFY, "true").lower() != "false"
