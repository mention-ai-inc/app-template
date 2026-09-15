import os
from argparse import ArgumentParser

from google.cloud import firestore

from library_provider_gcp.cloud.constants import FEATURE_PROJECT_ID

db = firestore.Client(project=FEATURE_PROJECT_ID)
feature_environment = os.environ["FEATURE_ENVIRONMENT"]


def list_collections(*, service: str | None) -> list[str]:
    prefix = f"{feature_environment}{service}" if service else feature_environment
    all_collections = db.collections()
    feature_environment_collections = [
        collection.id for collection in all_collections if collection.id.startswith(prefix)
    ]
    return feature_environment_collections


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--service", type=str)
    args = parser.parse_args()

    collections = list_collections(service=args.service)
    print(",".join(collections))
