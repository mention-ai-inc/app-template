import os
from typing import Any

import boto3

feature_environment = os.environ["FEATURE_ENVIRONMENT"]
sqs: Any = boto3.client("sqs", region_name=os.environ.get("AWS_REGION", "us-east-1"))


def list_feature_queue_urls() -> list[str]:
    urls: list[str] = []
    for page in sqs.get_paginator("list_queues").paginate(QueueNamePrefix=feature_environment):
        urls.extend(page.get("QueueUrls", []))
    return urls


def purge_all_queues() -> None:
    if not feature_environment:
        raise SystemExit("Refusing to purge queues without a feature environment prefix")

    queue_urls = list_feature_queue_urls()
    if not queue_urls:
        print(f"No task queues found for feature environment {feature_environment}")
        return

    for queue_url in queue_urls:
        try:
            sqs.purge_queue(QueueUrl=queue_url)
            print(f"Purged queue: {queue_url}")
        except Exception as error:
            print(f"Failed to purge queue {queue_url}: {error!s}")

    print("Task queue purge complete")


if __name__ == "__main__":
    purge_all_queues()
