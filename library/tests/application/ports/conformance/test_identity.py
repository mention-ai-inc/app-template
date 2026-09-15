import base64
import json
from typing import Any

from library.application.ports.identity import IIdentity

SERVICE = "notes"
PAYLOAD: dict[str, Any] = {"sub": "conformance", "scope": "read"}


def _decode_segment(segment: str, /) -> dict[str, Any]:
    padded = segment + "=" * (-len(segment) % 4)
    return json.loads(base64.urlsafe_b64decode(padded.encode()).decode())


class TestServiceIdentity:
    def test_the_service_identity_names_the_service(self, identity: IIdentity) -> None:
        service_identity = identity.service_identity(service=SERVICE)

        assert SERVICE in service_identity

    def test_different_services_get_different_identities(self, identity: IIdentity) -> None:
        assert identity.service_identity(service=SERVICE) != identity.service_identity(service="other")


class TestSignedTokens:
    async def test_a_signed_jwt_has_three_segments(self, identity: IIdentity) -> None:
        token = await identity.sign_jwt(identity=identity.service_identity(service=SERVICE), payload=PAYLOAD)

        assert len(token.split(".")) == 3

    async def test_the_payload_survives_the_signing(self, identity: IIdentity) -> None:
        token = await identity.sign_jwt(identity=identity.service_identity(service=SERVICE), payload=PAYLOAD)

        claims = _decode_segment(token.split(".")[1])
        assert {key: claims[key] for key in PAYLOAD} == PAYLOAD

    async def test_an_id_token_has_three_segments(self, identity: IIdentity) -> None:
        token = await identity.id_token(
            identity=identity.service_identity(service=SERVICE), audience="https://conformance.invalid"
        )

        assert len(token.split(".")) == 3


class TestVerifyingKeys:
    async def test_verifying_keys_are_a_non_empty_mapping(self, identity: IIdentity) -> None:
        keys = await identity.verifying_keys(identity=identity.service_identity(service=SERVICE))

        assert len(keys) > 0
        assert all(isinstance(key, str) and isinstance(value, str) for key, value in keys.items())
