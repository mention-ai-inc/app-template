import os


def scope_resource_name(resource_name: str, /) -> str:
    return os.getenv("FEATURE_ENVIRONMENT", "") + resource_name
