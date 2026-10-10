import os

from azure.identity import DefaultAzureCredential
from azure.servicebus import ServiceBusClient, ServiceBusReceiver, ServiceBusSubQueue

feature_environment = os.environ["FEATURE_ENVIRONMENT"]
namespace = os.environ["SERVICE_BUS_NAMESPACE"]
queue_names = [name for name in os.environ.get("SERVICE_BUS_QUEUE_NAMES", "").split(",") if name]
subscription_pairs = [pair for pair in os.environ.get("SERVICE_BUS_SUBSCRIPTION_PAIRS", "").split(",") if pair]

RECEIVE_BATCH_SIZE = 100
RECEIVE_WAIT_SECONDS = 2


def drain(receiver: ServiceBusReceiver, *, description: str) -> int:
    drained = 0
    with receiver:
        while True:
            messages = receiver.receive_messages(
                max_message_count=RECEIVE_BATCH_SIZE, max_wait_time=RECEIVE_WAIT_SECONDS
            )
            if not messages:
                break
            for message in messages:
                receiver.complete_message(message)
                drained += 1
    print(f"Drained {drained} messages from {description}")
    return drained


def purge_all_queues() -> None:
    if not feature_environment:
        raise SystemExit("Refusing to purge queues without a feature environment prefix")

    if not queue_names and not subscription_pairs:
        print(f"No task queues found for feature environment {feature_environment}")
        return

    with ServiceBusClient(fully_qualified_namespace=namespace, credential=DefaultAzureCredential()) as client:
        for queue_name in queue_names:
            for sub_queue in (None, ServiceBusSubQueue.DEAD_LETTER):
                label = queue_name if sub_queue is None else f"{queue_name} (dead letter)"
                drain(client.get_queue_receiver(queue_name=queue_name, sub_queue=sub_queue), description=label)

        for pair in subscription_pairs:
            topic_name, _, subscription_name = pair.partition(":")
            for sub_queue in (None, ServiceBusSubQueue.DEAD_LETTER):
                label = f"{topic_name}/{subscription_name}"
                if sub_queue is not None:
                    label = f"{label} (dead letter)"
                drain(
                    client.get_subscription_receiver(
                        topic_name=topic_name, subscription_name=subscription_name, sub_queue=sub_queue
                    ),
                    description=label,
                )

    print("Task queue purge complete")


if __name__ == "__main__":
    purge_all_queues()
