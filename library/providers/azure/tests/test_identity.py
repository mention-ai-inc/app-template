import base64
import json
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any, Self

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from pytest_mock import MockerFixture

from library.infrastructure.errors import InfrastructureError
from library_provider_azure.identity import AzureIdentity, AzureRuntimeContext
from library_provider_azure.settings import REGION, RESOURCE_GROUP, SUBSCRIPTION_ID

IDENTITY = "notes-s"
SIGNING_KEY_NAME = "notes-s-signing"


@dataclass
class FakeKeyProperties:
    version: str
    enabled: bool = True


@dataclass
class FakeJsonWebKey:
    n: bytes
    e: bytes


@dataclass
class FakeKey:
    name: str
    properties: FakeKeyProperties
    key: FakeJsonWebKey


@dataclass
class FakeSignature:
    signature: bytes


@dataclass
class FakeKeyClient:
    keys: dict[str, FakeKey]
    versions: list[FakeKeyProperties] = field(default_factory=list[FakeKeyProperties])
    requested: list[tuple[str, str | None]] = field(default_factory=list[tuple[str, str | None]])

    async def get_key(self, name: str, version: str | None = None) -> FakeKey:
        self.requested.append((name, version))
        return self.keys[name]

    async def list_properties_of_key_versions(self, name: str) -> AsyncGenerator[FakeKeyProperties]:  # noqa: ARG002
        for version in self.versions:
            yield version


class FakeCryptographyClient:
    def __init__(self, *_: object, **__: object) -> None:
        return None

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def sign(self, _algorithm: object, digest: bytes) -> FakeSignature:
        return FakeSignature(signature=digest)


def to_bytes(value: int, /) -> bytes:
    return value.to_bytes((value.bit_length() + 7) // 8, "big")


def make_key(*, version: str) -> FakeKey:
    numbers = rsa.generate_private_key(public_exponent=65537, key_size=2048).public_key().public_numbers()
    return FakeKey(
        name=SIGNING_KEY_NAME,
        properties=FakeKeyProperties(version=version),
        key=FakeJsonWebKey(n=to_bytes(numbers.n), e=to_bytes(numbers.e)),
    )


def decode_segment(segment: str, /) -> dict[str, Any]:
    return json.loads(base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4)).decode())


@pytest.fixture
def key_client(mocker: MockerFixture) -> FakeKeyClient:
    client = FakeKeyClient(keys={SIGNING_KEY_NAME: make_key(version="v1")}, versions=[FakeKeyProperties(version="v1")])
    mocker.patch("library_provider_azure.identity.AzureClients.keys", return_value=client)
    mocker.patch("library_provider_azure.identity.AzureClients.credential", return_value=None)
    mocker.patch("library_provider_azure.identity.CryptographyClient", FakeCryptographyClient)
    return client


class TestServiceIdentity:
    def test_the_identity_is_the_managed_identity_the_estate_creates(self) -> None:
        assert AzureIdentity().service_identity(service="notes") == IDENTITY

    def test_the_feature_environment_scopes_the_identity(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("FEATURE_ENVIRONMENT", "pr7")

        assert AzureIdentity().service_identity(service="notes") == "pr7notes-s"


class TestSigning:
    async def test_a_signed_token_has_three_segments(self, key_client: FakeKeyClient) -> None:  # noqa: ARG002
        token = await AzureIdentity().sign_jwt(identity=IDENTITY, payload={"sub": "conformance"})

        assert len(token.split(".")) == 3

    async def test_the_payload_and_the_issuer_survive_the_signing(self, key_client: FakeKeyClient) -> None:  # noqa: ARG002
        token = await AzureIdentity().sign_jwt(identity=IDENTITY, payload={"sub": "conformance"})

        claims = decode_segment(token.split(".")[1])
        assert claims["sub"] == "conformance"
        assert claims["iss"] == IDENTITY

    async def test_the_header_names_the_key_version_so_a_verifier_can_find_the_public_key(
        self,
        key_client: FakeKeyClient,  # noqa: ARG002
    ) -> None:
        token = await AzureIdentity().sign_jwt(identity=IDENTITY, payload={})

        assert decode_segment(token.split(".")[0]) == {"alg": "RS256", "kid": "v1", "typ": "JWT"}

    async def test_signing_uses_the_key_vault_key_named_after_the_identity(self, key_client: FakeKeyClient) -> None:
        await AzureIdentity().sign_jwt(identity=IDENTITY, payload={})

        assert key_client.requested[0] == (SIGNING_KEY_NAME, None)


class TestVerifyingKeys:
    async def test_every_enabled_version_is_offered_as_a_pem_public_key(self, key_client: FakeKeyClient) -> None:
        key_client.versions = [FakeKeyProperties(version="v1"), FakeKeyProperties(version="v2")]

        keys = await AzureIdentity().verifying_keys(identity=IDENTITY)

        assert sorted(keys) == ["v1", "v2"]
        assert all(pem.startswith("-----BEGIN PUBLIC KEY-----") for pem in keys.values())

    async def test_a_disabled_version_cannot_verify_anything(self, key_client: FakeKeyClient) -> None:
        key_client.versions = [FakeKeyProperties(version="v1"), FakeKeyProperties(version="v2", enabled=False)]

        assert sorted(await AzureIdentity().verifying_keys(identity=IDENTITY)) == ["v1"]

    async def test_the_keys_are_cached_between_calls(self, key_client: FakeKeyClient) -> None:
        identity = AzureIdentity()

        await identity.verifying_keys(identity=IDENTITY)
        await identity.verifying_keys(identity=IDENTITY)

        assert len(key_client.requested) == 1

    async def test_a_refresh_goes_back_to_key_vault_for_a_key_the_cache_has_never_seen(
        self, key_client: FakeKeyClient
    ) -> None:
        identity = AzureIdentity()
        await identity.verifying_keys(identity=IDENTITY)

        refreshed = await identity.verifying_keys(identity=IDENTITY, refresh=True)

        assert len(key_client.requested) == 2
        assert sorted(refreshed) == ["v1"]


class TestRuntimeContext:
    def test_the_deployment_is_the_resource_group_the_service_runs_in(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(RESOURCE_GROUP, "acme-production")

        assert AzureRuntimeContext().get_deployment_id() == "acme-production"

    def test_the_subscription_names_the_deployment_when_the_resource_group_does_not(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv(RESOURCE_GROUP, raising=False)
        monkeypatch.setenv(SUBSCRIPTION_ID, "00000000-0000-0000-0000-000000000000")

        assert AzureRuntimeContext().get_deployment_id() == "00000000-0000-0000-0000-000000000000"

    def test_an_unnamed_deployment_is_an_environment_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(RESOURCE_GROUP, raising=False)
        monkeypatch.delenv(SUBSCRIPTION_ID, raising=False)

        with pytest.raises(InfrastructureError):
            AzureRuntimeContext().get_deployment_id()

    def test_the_region_comes_from_the_environment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(REGION, "westeurope")

        assert AzureRuntimeContext().get_region() == "westeurope"

    def test_scoping_reads_the_feature_environment_on_every_call(self, monkeypatch: pytest.MonkeyPatch) -> None:
        runtime_context = AzureRuntimeContext()
        monkeypatch.setenv("FEATURE_ENVIRONMENT", "")
        assert runtime_context.scope_resource_name("notes-commands") == "notes-commands"

        monkeypatch.setenv("FEATURE_ENVIRONMENT", "pr7")

        assert runtime_context.scope_resource_name("notes-commands") == "pr7notes-commands"
