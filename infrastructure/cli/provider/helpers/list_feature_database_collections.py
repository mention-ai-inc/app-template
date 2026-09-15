import os
from argparse import ArgumentParser
from typing import Any

import boto3

from library_provider_aws.transactions import COLLECTION_ATTRIBUTE

feature_environment = os.environ["FEATURE_ENVIRONMENT"]
table_name = os.environ.get("DYNAMODB_TABLE_NAME") or f"{feature_environment}acme"
dynamodb: Any = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
table: Any = dynamodb.Table(table_name)


def list_collections(*, service: str | None) -> list[str]:
    prefix = f"{feature_environment}{service}" if service else feature_environment
    collections: set[str] = set()
    arguments: dict[str, Any] = {
        "ProjectionExpression": "#collection",
        "ExpressionAttributeNames": {"#collection": COLLECTION_ATTRIBUTE},
    }
    while True:
        page: dict[str, Any] = table.scan(**arguments)
        for item in page.get("Items", []):
            collection = item.get(COLLECTION_ATTRIBUTE)
            if isinstance(collection, str) and collection.startswith(prefix):
                collections.add(collection)
        cursor = page.get("LastEvaluatedKey")
        if not cursor:
            break
        arguments["ExclusiveStartKey"] = cursor
    return sorted(collections)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--service", type=str)
    args = parser.parse_args()

    print(",".join(list_collections(service=args.service)))
