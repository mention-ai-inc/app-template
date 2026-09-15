import os
from argparse import ArgumentParser
from typing import Any, cast

from azure.cosmos import CosmosClient, DatabaseProxy
from azure.identity import DefaultAzureCredential

from library_provider_azure.documents import DOCUMENT_TYPE_FIELD

feature_environment = os.environ["FEATURE_ENVIRONMENT"]
database_name = os.environ.get("COSMOS_DATABASE") or f"{feature_environment}acme"
endpoint = os.environ["COSMOS_ENDPOINT"]


def database() -> DatabaseProxy:
    client = CosmosClient(url=endpoint, credential=DefaultAzureCredential())
    return client.get_database_client(database_name)


def list_collections(*, service: str | None) -> list[str]:
    prefix = f"{feature_environment}{service}" if service else feature_environment
    collections: set[str] = set()

    for container_properties in database().list_containers():
        container = database().get_container_client(cast(str, container_properties["id"]))
        query = f"SELECT DISTINCT VALUE c.{DOCUMENT_TYPE_FIELD} FROM c"
        for document_type in cast(Any, container.query_items(query=query, enable_cross_partition_query=True)):
            if isinstance(document_type, str) and document_type.startswith(prefix):
                collections.add(document_type)

    return sorted(collections)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--service", type=str)
    args = parser.parse_args()

    print(",".join(list_collections(service=args.service)))
