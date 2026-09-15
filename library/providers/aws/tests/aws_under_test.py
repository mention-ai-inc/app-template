import base64
import json
from datetime import UTC, datetime, timedelta
from typing import Any

import boto3
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from tests.application.ports.conformance.providers import ProviderUnderTest, RecordedMessage, RecordedTask

from library.domain.value_objects.common import Service
from library.infrastructure.persistence.storage import BucketName
from library_provider_aws import operators
from library_provider_aws.clients import get_collection_index_name
from library_provider_aws.identity import reset_verifying_keys
from library_provider_aws.operators import OIDC_DATA_HEADER
from library_provider_aws.provider import PROVIDER as AWS_PROVIDER
from library_provider_aws.transactions import (
    COLLECTION_ATTRIBUTE,
    DOCUMENT_ID_ATTRIBUTE,
    PARTITION_KEY_ATTRIBUTE,
    SORT_KEY_ATTRIBUTE,
)

ACCOUNT_ID = "123456789012"
CONFORMANCE_TOPIC = "conformance-topic"
RECORDER_QUEUE = "conformance-recorder"
TASK_QUEUE = "notes-c-reindex"
SECRET_NAME = "conformance-secret"
SECRET_VALUE = "conformance-secret-value"
SIGNING_KEY_ALIAS = "alias/notes-s"
TABLE_NAME = "acme-documents"
CONFORMANCE_BUCKET_NAME = f"{ACCOUNT_ID}--{Service.NOTES.value}-{BucketName.CACHE.value}"
DRAIN_ATTEMPTS = 50


class AwsEstate:
    def __init__(self, *, endpoint_url: str, region: str) -> None:
        self._keywords: dict[str, Any] = {"endpoint_url": endpoint_url, "region_name": region}
        self._topic_arn = ""
        self._recorder_queue_url = ""
        self._task_queue_url = ""

    def create(self) -> None:
        self.__create_table()
        self.__create_bucket()
        self.__create_messaging()
        self.__create_secret()
        self.__create_signing_key()

    def reset(self) -> None:
        reset_verifying_keys()
        self.__clear_table()
        self.__clear_bucket()
        self.__drain(self._recorder_queue_url)
        self.__drain(self._task_queue_url)

    def recorded_messages(self) -> list[RecordedMessage]:
        recorded: list[RecordedMessage] = []
        for body in self.__drain(self._recorder_queue_url):
            notification = json.loads(body)
            recorded.append(
                RecordedMessage(
                    topic_name=str(notification["TopicArn"]).rsplit(":", 1)[-1],
                    data=notification["Message"],
                    attributes={
                        name: attribute["Value"]
                        for name, attribute in notification.get("MessageAttributes", {}).items()
                    },
                    message_id=notification["MessageId"],
                )
            )
        return recorded

    def recorded_tasks(self) -> list[RecordedTask]:
        recorded: list[RecordedTask] = []
        for body in self.__drain(self._task_queue_url):
            envelope = json.loads(body)
            scheduled_time = envelope["scheduled_time"]
            recorded.append(
                RecordedTask(
                    service=envelope["service"],
                    task=envelope["task"],
                    body=envelope["body"],
                    params=envelope["params"],
                    headers=envelope["headers"],
                    scheduled_time=None if scheduled_time is None else datetime.fromisoformat(scheduled_time),
                )
            )
        return recorded

    def __client(self, service_name: str, /) -> Any:
        return boto3.client(service_name, **self._keywords)  # pyright: ignore[reportUnknownMemberType]

    def __create_table(self) -> None:
        dynamodb = self.__client("dynamodb")
        if TABLE_NAME in dynamodb.list_tables()["TableNames"]:
            return

        dynamodb.create_table(
            TableName=TABLE_NAME,
            BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[
                {"AttributeName": PARTITION_KEY_ATTRIBUTE, "AttributeType": "S"},
                {"AttributeName": SORT_KEY_ATTRIBUTE, "AttributeType": "S"},
                {"AttributeName": COLLECTION_ATTRIBUTE, "AttributeType": "S"},
                {"AttributeName": DOCUMENT_ID_ATTRIBUTE, "AttributeType": "S"},
            ],
            KeySchema=[
                {"AttributeName": PARTITION_KEY_ATTRIBUTE, "KeyType": "HASH"},
                {"AttributeName": SORT_KEY_ATTRIBUTE, "KeyType": "RANGE"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": get_collection_index_name(),
                    "KeySchema": [
                        {"AttributeName": COLLECTION_ATTRIBUTE, "KeyType": "HASH"},
                        {"AttributeName": DOCUMENT_ID_ATTRIBUTE, "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
        )

    def __clear_table(self) -> None:
        dynamodb = self.__client("dynamodb")
        paginator = dynamodb.get_paginator("scan")
        for page in paginator.paginate(TableName=TABLE_NAME):
            for item in page["Items"]:
                dynamodb.delete_item(
                    TableName=TABLE_NAME,
                    Key={
                        PARTITION_KEY_ATTRIBUTE: item[PARTITION_KEY_ATTRIBUTE],
                        SORT_KEY_ATTRIBUTE: item[SORT_KEY_ATTRIBUTE],
                    },
                )

    def __create_bucket(self) -> None:
        s3 = self.__client("s3")
        if CONFORMANCE_BUCKET_NAME not in [bucket["Name"] for bucket in s3.list_buckets()["Buckets"]]:
            s3.create_bucket(Bucket=CONFORMANCE_BUCKET_NAME)

    def __clear_bucket(self) -> None:
        s3 = self.__client("s3")
        for page in s3.get_paginator("list_objects_v2").paginate(Bucket=CONFORMANCE_BUCKET_NAME):
            for stored in page.get("Contents", []):
                s3.delete_object(Bucket=CONFORMANCE_BUCKET_NAME, Key=stored["Key"])

    def __create_messaging(self) -> None:
        sns = self.__client("sns")
        sqs = self.__client("sqs")

        self._topic_arn = sns.create_topic(Name=CONFORMANCE_TOPIC)["TopicArn"]
        self._recorder_queue_url = sqs.create_queue(QueueName=RECORDER_QUEUE)["QueueUrl"]
        self._task_queue_url = sqs.create_queue(QueueName=TASK_QUEUE)["QueueUrl"]

        recorder_arn = sqs.get_queue_attributes(QueueUrl=self._recorder_queue_url, AttributeNames=["QueueArn"])[
            "Attributes"
        ]["QueueArn"]
        sns.subscribe(TopicArn=self._topic_arn, Protocol="sqs", Endpoint=recorder_arn)

    def __create_secret(self) -> None:
        secretsmanager = self.__client("secretsmanager")
        existing = [secret["Name"] for secret in secretsmanager.list_secrets()["SecretList"]]
        if SECRET_NAME in existing:
            return

        secretsmanager.create_secret(Name=SECRET_NAME, SecretString=SECRET_VALUE)
        secretsmanager.put_secret_value(SecretId=SECRET_NAME, SecretString=SECRET_VALUE, VersionStages=["1"])

    def __create_signing_key(self) -> None:
        kms = self.__client("kms")
        if SIGNING_KEY_ALIAS in [alias["AliasName"] for alias in kms.list_aliases()["Aliases"]]:
            return

        key = kms.create_key(KeyUsage="SIGN_VERIFY", KeySpec="RSA_2048")
        kms.create_alias(AliasName=SIGNING_KEY_ALIAS, TargetKeyId=key["KeyMetadata"]["KeyId"])

    def __drain(self, queue_url: str, /) -> list[str]:
        if queue_url == "":
            return []

        sqs = self.__client("sqs")
        bodies: list[str] = []
        for _ in range(DRAIN_ATTEMPTS):
            received = sqs.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=10, WaitTimeSeconds=0)
            messages = received.get("Messages", [])
            if len(messages) == 0:
                return bodies
            for message in messages:
                bodies.append(message["Body"])
                sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=message["ReceiptHandle"])
        return bodies


_estate: AwsEstate | None = None


def get_estate() -> AwsEstate:
    if _estate is None:
        raise RuntimeError("The AWS conformance estate has not been started")
    return _estate


def set_estate(estate: AwsEstate, /) -> None:
    global _estate
    _estate = estate


OPERATOR_KEY_ID = "conformance-key"
OPERATOR_SUBJECT = "operator-subject"
OPERATOR_EMAIL = "conformance@acme.example.com"

_operator_key = ec.generate_private_key(ec.SECP256R1())


def mint_operator_assertion(
    *,
    email: str | None = OPERATOR_EMAIL,
    key_id: str = OPERATOR_KEY_ID,
    signing_key: ec.EllipticCurvePrivateKey | None = None,
    expires_in_seconds: int = 600,
) -> str:
    operators._public_keys[OPERATOR_KEY_ID] = (  # pyright: ignore[reportPrivateUsage]
        _operator_key.public_key()
        .public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "iss": "https://clerk.acme.example.com",
        "sub": OPERATOR_SUBJECT,
        "exp": now + timedelta(seconds=expires_in_seconds),
    }
    if email is not None:
        payload["email"] = email
    return jwt.encode(payload, signing_key or _operator_key, algorithm="ES256", headers={"kid": key_id})


def operator_headers() -> dict[str, str]:
    return {OIDC_DATA_HEADER: mint_operator_assertion()}


AWS = ProviderUnderTest(
    name="aws",
    factory=lambda: AWS_PROVIDER,
    reset=lambda: get_estate().reset(),
    recorded_messages=lambda: get_estate().recorded_messages(),
    recorded_tasks=lambda: get_estate().recorded_tasks(),
    operator_headers=operator_headers,
    install_conformance_job=None,
)


def decode_message_data(data: str, /) -> str:
    return base64.b64decode(data).decode()
