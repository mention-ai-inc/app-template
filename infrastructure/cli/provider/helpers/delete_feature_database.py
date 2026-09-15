import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from google.cloud import firestore

from library_provider_gcp.cloud.constants import FEATURE_PROJECT_ID

db = firestore.Client(project=FEATURE_PROJECT_ID)
feature_environment = os.environ["FEATURE_ENVIRONMENT"]


def list_collections() -> list[str]:
    all_collections = db.collections()
    feature_environment_collections = [
        collection.id for collection in all_collections if collection.id.startswith(feature_environment)
    ]
    return feature_environment_collections


def _delete_single_collection(collection_id: str) -> None:
    print(f"Deleting collection: {collection_id}")
    collection_ref = db.collection(collection_id)
    num_deleted = db.recursive_delete(collection_ref)
    print(f"Deleted {num_deleted} documents from collection: {collection_id}")


def delete_feature_environment() -> None:
    print(f"Deleting database for feature environment '{feature_environment}'")

    feature_environment_collections = list_collections()
    if not feature_environment_collections:
        print(f"Database for feature environment {feature_environment} deleted")
        return

    max_workers = min(8, len(feature_environment_collections))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_delete_single_collection, collection_id): collection_id
            for collection_id in feature_environment_collections
        }
        for future in as_completed(futures):
            future.result()

    print(f"Database for feature environment {feature_environment} deleted")


if __name__ == "__main__":
    delete_feature_environment()
