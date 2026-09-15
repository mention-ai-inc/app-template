from enum import StrEnum

from library.domain.value_objects.common import Service
from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType


def ObjectNotFoundError(filepath: str) -> InfrastructureError:
    return InfrastructureError(
        error_type=InfrastructureErrorType.CLOUD_ERROR, message=f"Object {filepath} not found in object storage"
    )


class BucketName(StrEnum):
    CACHE = "cache"


SERVICE_BUCKETS = {
    Service.NOTES: [BucketName.CACHE],
}
