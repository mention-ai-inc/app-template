import os
from functools import lru_cache

import httpx

from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType


@lru_cache
def get_project_id() -> str:
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    if project is None:
        response = httpx.get(
            "http://metadata.google.internal/computeMetadata/v1/project/project-id",
            headers={"Metadata-Flavor": "Google"},
        )

        if response.status_code != 200:
            raise InfrastructureError(
                error_type=InfrastructureErrorType.ENVIRONMENT_ERROR,
                message=f"Failed to get project ID from metadata server. Status code: {response.status_code}",
            )

        project = response.text
        if not project:
            raise InfrastructureError(
                error_type=InfrastructureErrorType.ENVIRONMENT_ERROR,
                message="Failed to get project ID from metadata server. No project ID found.",
            )

    return project
