import asyncio
import os

from library.domain.value_objects.common import Service
from library.infrastructure.errors import InfrastructureError
from library.infrastructure.persistence.storage import BucketName
from library.providers.registry import get_cloud_provider

feature_environment = os.environ["FEATURE_ENVIRONMENT"]


async def clear_storage_bucket_async() -> None:
    """Clear all objects from the feature environment's object storage."""
    provider = get_cloud_provider()
    for service in Service:
        for bucket in BucketName:
            try:
                storage = provider.blob_store(service=service, bucket=bucket)
            except InfrastructureError:
                continue

            try:
                await storage.delete_all_under(prefix="")
                print(f"Cleared {service.value}/{bucket.value} for feature environment {feature_environment}")
            except Exception as e:
                print(f"Error accessing bucket {bucket.value}: {str(e)}")
                raise


if __name__ == "__main__":
    asyncio.run(clear_storage_bucket_async())
