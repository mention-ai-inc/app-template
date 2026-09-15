import asyncio
import os

from library_provider_gcp.cloud.constants import FEATURE_PROJECT_ID, REGION
from library_provider_gcp.cloud.tasks import Tasks

feature_environment = os.environ["FEATURE_ENVIRONMENT"]


async def purge_all_queues() -> None:
    """Purges all tasks from all queues in the given feature environment."""
    tasks_client = Tasks()

    queues_response = await tasks_client.client.get(f"/projects/{FEATURE_PROJECT_ID}/locations/{REGION}/queues")
    queues_response.raise_for_status()
    queues = queues_response.json().get("queues", [])

    feature_queues = [queue for queue in queues if queue["name"].split("/")[-1].startswith(feature_environment)]

    if not feature_queues:
        print(f"No task queues found for feature environment {feature_environment}")
        return

    for queue in feature_queues:
        try:
            purge_response = await tasks_client.client.post(f"{queue['name']}:purge")
            purge_response.raise_for_status()
            print(f"Purged queue: {queue['name']}")
        except Exception as e:
            print(f"Failed to purge queue {queue['name']}: {str(e)}")

    print("Task queue purge complete")


if __name__ == "__main__":
    asyncio.run(purge_all_queues())
