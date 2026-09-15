import base64
import hashlib
import json
import os
from typing import Any, cast

from azure.keyvault.keys import KeyVaultKey
from azure.keyvault.keys.crypto import SignatureAlgorithm
from azure.keyvault.keys.crypto.aio import CryptographyClient
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType
from library_provider_azure.clients import AzureClients
from library_provider_azure.settings import (
    DEFAULT_REGION,
    REGION,
    RESOURCE_GROUP,
    SUBSCRIPTION_ID,
    feature_environment,
)

SIGNING_KEY_SUFFIX = "-signing"


def encode_segment(claims: dict[str, Any], /) -> str:
    return (
        base64.urlsafe_b64encode(json.dumps(claims, default=str, separators=(",", ":")).encode()).decode().rstrip("=")
    )


def to_pem(key: KeyVaultKey, /) -> str:
    jwk = cast(Any, key.key)
    modulus = cast(bytes | None, getattr(jwk, "n", None))
    exponent = cast(bytes | None, getattr(jwk, "e", None))

    if modulus is None or exponent is None:
        raise InfrastructureError(
            error_type=InfrastructureErrorType.CLOUD_ERROR,
            message=f"Key Vault key {key.name} is not an RSA key, so it cannot verify a service token",
        )

    public_numbers = rsa.RSAPublicNumbers(
        e=int.from_bytes(exponent, "big"),
        n=int.from_bytes(modulus, "big"),
    )
    return (
        public_numbers.public_key()
        .public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )


class AzureIdentity:
    def __init__(self) -> None:
        self._verifying_keys: dict[str, dict[str, str]] = {}

    def service_identity(self, *, service: str) -> str:
        return f"{feature_environment()}{service}-s"

    async def sign_jwt(self, *, identity: str, payload: dict[str, Any]) -> str:
        key = await AzureClients.keys().get_key(self.__signing_key_name(identity))
        header = encode_segment({"alg": SignatureAlgorithm.rs256.value, "kid": self.__key_id(key), "typ": "JWT"})
        body = encode_segment({**payload, "iss": identity})
        digest = hashlib.sha256(f"{header}.{body}".encode()).digest()

        async with CryptographyClient(key, credential=AzureClients.credential()) as crypto:
            signed = await crypto.sign(SignatureAlgorithm.rs256, digest)

        signature = base64.urlsafe_b64encode(signed.signature).decode().rstrip("=")
        return f"{header}.{body}.{signature}"

    async def id_token(self, *, identity: str, audience: str) -> str:  # noqa: ARG002
        token = await AzureClients.credential().get_token(f"{audience.rstrip('/')}/.default")
        return token.token

    async def verifying_keys(self, *, identity: str, refresh: bool = False) -> dict[str, str]:
        if refresh:
            self._verifying_keys.pop(identity, None)
        elif identity in self._verifying_keys:
            return self._verifying_keys[identity]

        key_name = self.__signing_key_name(identity)
        keys = AzureClients.keys()
        public_keys: dict[str, str] = {}

        async for version in keys.list_properties_of_key_versions(key_name):
            if version.enabled is False or version.version is None:
                continue
            public_keys[version.version] = to_pem(await keys.get_key(key_name, version.version))

        self._verifying_keys[identity] = public_keys
        return public_keys

    def __signing_key_name(self, identity: str, /) -> str:
        return f"{identity}{SIGNING_KEY_SUFFIX}"

    def __key_id(self, key: KeyVaultKey, /) -> str:
        version = key.properties.version
        if version is None:
            raise InfrastructureError(
                error_type=InfrastructureErrorType.CLOUD_ERROR,
                message=f"Key Vault key {key.name} has no version to use as a token key id",
            )
        return version


class AzureRuntimeContext:
    def get_deployment_id(self) -> str:
        deployment_id = os.getenv(RESOURCE_GROUP) or os.getenv(SUBSCRIPTION_ID)
        if not deployment_id:
            raise InfrastructureError(
                error_type=InfrastructureErrorType.ENVIRONMENT_ERROR,
                message=f"Neither {RESOURCE_GROUP} nor {SUBSCRIPTION_ID} is set, so there is no deployment to name",
            )
        return deployment_id

    def get_region(self) -> str:
        return os.getenv(REGION) or DEFAULT_REGION

    def scope_resource_name(self, resource_name: str, /) -> str:
        return os.getenv("FEATURE_ENVIRONMENT", "") + resource_name
