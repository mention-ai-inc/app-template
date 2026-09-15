import os
from typing import Any

import boto3

from library_provider_aws.transactions import PARTITION_KEY_ATTRIBUTE, SORT_KEY_ATTRIBUTE

feature_environment = os.environ["FEATURE_ENVIRONMENT"]
table_name = os.environ.get("DYNAMODB_TABLE_NAME") or f"{feature_environment}acme"
dynamodb: Any = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
table: Any = dynamodb.Table(table_name)


def delete_feature_environment() -> None:
    if not feature_environment or not table_name.startswith(feature_environment):
        raise SystemExit(
            f"Refusing to empty '{table_name}': it is not the table of feature environment '{feature_environment}'"
        )

    print(f"Deleting every document in '{table_name}' for feature environment '{feature_environment}'")

    deleted = 0
    arguments: dict[str, Any] = {"ProjectionExpression": f"{PARTITION_KEY_ATTRIBUTE}, {SORT_KEY_ATTRIBUTE}"}
    while True:
        page: dict[str, Any] = table.scan(**arguments)
        items: list[dict[str, Any]] = page.get("Items", [])
        if items:
            with table.batch_writer() as batch:
                for item in items:
                    batch.delete_item(
                        Key={
                            PARTITION_KEY_ATTRIBUTE: item[PARTITION_KEY_ATTRIBUTE],
                            SORT_KEY_ATTRIBUTE: item[SORT_KEY_ATTRIBUTE],
                        }
                    )
                    deleted += 1
        cursor = page.get("LastEvaluatedKey")
        if not cursor:
            break
        arguments["ExclusiveStartKey"] = cursor

    print(f"Deleted {deleted} documents from '{table_name}'")


if __name__ == "__main__":
    delete_feature_environment()
