import os
from typing import Any, cast

from azure.cosmos import CosmosClient, DatabaseProxy
from azure.identity import DefaultAzureCredential

from library_provider_azure.documents import PARTITION_KEY_FIELD

feature_environment = os.environ["FEATURE_ENVIRONMENT"]
database_name = os.environ.get("COSMOS_DATABASE") or f"{feature_environment}acme"
endpoint = os.environ["COSMOS_ENDPOINT"]


def database() -> DatabaseProxy:
    client = CosmosClient(url=endpoint, credential=DefaultAzureCredential())
    return client.get_database_client(database_name)


def delete_feature_environment() -> None:
    if not feature_environment or not database_name.startswith(feature_environment):
        raise SystemExit(
            f"Refusing to empty '{database_name}': it is not the database of feature environment "
            f"'{feature_environment}'"
        )

    print(f"Deleting every document in '{database_name}' for feature environment '{feature_environment}'")

    feature_database = database()
    deleted = 0
    for container_properties in feature_database.list_containers():
        container_name = cast(str, container_properties["id"])
        container = feature_database.get_container_client(container_name)
        query = f"SELECT c.id, c.{PARTITION_KEY_FIELD} FROM c"
        items = list(cast(Any, container.query_items(query=query, enable_cross_partition_query=True)))
        for item in items:
            container.delete_item(item=cast(str, item["id"]), partition_key=item[PARTITION_KEY_FIELD])
            deleted += 1
        print(f"Deleted {len(items)} documents from container '{container_name}'")

    print(f"Deleted {deleted} documents from '{database_name}'")


if __name__ == "__main__":
    delete_feature_environment()
