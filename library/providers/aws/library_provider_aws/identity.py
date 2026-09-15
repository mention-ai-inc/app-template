import base64
import json
import os
from typing import Any

from library_provider_aws.clients import client, get_account_id, get_region, scope_resource_name

SIGNING_ALGORITHM = "RSASSA_PKCS1_V1_5_SHA_256"
JWT_ALGORITHM = "RS256"
SERVICE_ROLE_SUFFIX = "-s"

_public_keys: dict[str, dict[str, str]] = {}


class KmsIdentity:
    def service_identity(self, *, service: str) -> str:
        return f"arn:aws:iam::{get_account_id()}:role/{scope_resource_name(service)}{SERVICE_ROLE_SUFFIX}"

    def signing_key_alias(self, *, identity: str) -> str:
        return f"alias/{identity.rsplit('/', 1)[-1]}"

    async def sign_jwt(self, *, identity: str, payload: dict[str, Any]) -> str:
        key_alias = self.signing_key_alias(identity=identity)

        async with client("kms") as kms:
            key_id = str((await kms.describe_key(KeyId=key_alias))["KeyMetadata"]["KeyId"])
            header = self.__encode({"alg": JWT_ALGORITHM, "typ": "JWT", "kid": key_id})
            body = self.__encode({**payload, "iss": identity})
            signing_input = f"{header}.{body}"
            signed = await kms.sign(
                KeyId=key_alias,
                Message=signing_input.encode(),
                MessageType="RAW",
                SigningAlgorithm=SIGNING_ALGORITHM,
            )

        signature = base64.urlsafe_b64encode(bytes(signed["Signature"])).decode().rstrip("=")
        return f"{signing_input}.{signature}"

    async def id_token(self, *, identity: str, audience: str) -> str:
        return await self.sign_jwt(identity=identity, payload={"aud": audience})

    async def verifying_keys(self, *, identity: str, refresh: bool = False) -> dict[str, str]:
        if not refresh and identity in _public_keys:
            return _public_keys[identity]

        async with client("kms") as kms:
            response = await kms.get_public_key(KeyId=self.signing_key_alias(identity=identity))

        key_id = str(response["KeyId"]).rsplit("/", 1)[-1]
        _public_keys[identity] = {key_id: self.__to_pem(bytes(response["PublicKey"]))}
        return _public_keys[identity]

    def __encode(self, claims: dict[str, Any], /) -> str:
        serialized = json.dumps(claims, default=str, sort_keys=True).encode()
        return base64.urlsafe_b64encode(serialized).decode().rstrip("=")

    def __to_pem(self, der_public_key: bytes, /) -> str:
        body = base64.b64encode(der_public_key).decode()
        lines = [body[start : start + 64] for start in range(0, len(body), 64)]
        return "\n".join(["-----BEGIN PUBLIC KEY-----", *lines, "-----END PUBLIC KEY-----", ""])


class AwsRuntimeContext:
    def get_deployment_id(self) -> str:
        return get_account_id()

    def get_region(self) -> str:
        return get_region()

    def scope_resource_name(self, resource_name: str, /) -> str:
        return os.getenv("FEATURE_ENVIRONMENT", "") + resource_name


def reset_verifying_keys() -> None:
    _public_keys.clear()
