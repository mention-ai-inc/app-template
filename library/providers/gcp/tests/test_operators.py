import json
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from jwt.algorithms import ECAlgorithm

from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType
from library_provider_gcp import operators
from library_provider_gcp.operators import IAP_ASSERTION_HEADER, IAP_ISSUER, IapOperatorAuth

AUDIENCE = "/projects/000000000002/global/backendServices/1234567890"
KID = "test-kid"
SUBJECT = "accounts.google.com:12345"
OPERATOR_EMAIL = "engineer@acme.example.com"


@pytest.fixture
def signing_key() -> ec.EllipticCurvePrivateKey:
    return ec.generate_private_key(ec.SECP256R1())


@pytest.fixture(autouse=True)
def iap_estate(monkeypatch: pytest.MonkeyPatch, signing_key: ec.EllipticCurvePrivateKey) -> Generator[None]:
    jwk = json.loads(ECAlgorithm.to_jwk(signing_key.public_key()))
    jwk["kid"] = KID
    jwk["alg"] = "ES256"
    signing_keys = {KID: jwk}

    async def fetch_signing_keys() -> dict[str, Any]:
        return signing_keys

    monkeypatch.setattr(operators, "_signing_keys", dict(signing_keys))
    monkeypatch.setattr(operators, "_fetch_signing_keys", fetch_signing_keys)
    monkeypatch.setattr(operators, "_audience", AUDIENCE)
    yield
    operators.reset_iap_cache()


def _assertion(
    signing_key: ec.EllipticCurvePrivateKey,
    *,
    email: str | None = OPERATOR_EMAIL,
    issuer: str = IAP_ISSUER,
    audience: str = AUDIENCE,
    kid: str = KID,
    expires_in_seconds: int = 600,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "iss": issuer,
        "aud": audience,
        "iat": now - timedelta(seconds=30),
        "exp": now + timedelta(seconds=expires_in_seconds),
        "sub": SUBJECT,
    }
    if email is not None:
        payload["email"] = email
    return jwt.encode(payload, signing_key, algorithm="ES256", headers={"kid": kid})


async def _refused(headers: dict[str, str]) -> InfrastructureErrorType:
    with pytest.raises(InfrastructureError) as error:
        await IapOperatorAuth().authenticate(headers=headers)
    return error.value.error_type


async def test_a_valid_assertion_identifies_the_operator(signing_key: ec.EllipticCurvePrivateKey) -> None:
    operator = await IapOperatorAuth().authenticate(headers={IAP_ASSERTION_HEADER: _assertion(signing_key)})

    assert operator.subject == SUBJECT
    assert operator.email == OPERATOR_EMAIL


async def test_a_missing_assertion_fails_closed() -> None:
    assert await _refused({}) == InfrastructureErrorType.OAUTH_ERROR


async def test_a_garbage_assertion_is_rejected() -> None:
    assert await _refused({IAP_ASSERTION_HEADER: "not-a-jwt"}) == InfrastructureErrorType.OAUTH_ERROR


async def test_a_wrong_issuer_is_rejected(signing_key: ec.EllipticCurvePrivateKey) -> None:
    assertion = _assertion(signing_key, issuer="https://accounts.google.com")

    assert await _refused({IAP_ASSERTION_HEADER: assertion}) == InfrastructureErrorType.OAUTH_ERROR


async def test_a_wrong_audience_is_rejected(signing_key: ec.EllipticCurvePrivateKey) -> None:
    assertion = _assertion(signing_key, audience="/projects/999/global/backendServices/1")

    assert await _refused({IAP_ASSERTION_HEADER: assertion}) == InfrastructureErrorType.OAUTH_ERROR


async def test_an_expired_assertion_is_rejected(signing_key: ec.EllipticCurvePrivateKey) -> None:
    assertion = _assertion(signing_key, expires_in_seconds=-60)

    assert await _refused({IAP_ASSERTION_HEADER: assertion}) == InfrastructureErrorType.OAUTH_ERROR


async def test_an_unknown_signing_key_is_rejected(signing_key: ec.EllipticCurvePrivateKey) -> None:
    assertion = _assertion(signing_key, kid="unknown-kid")

    assert await _refused({IAP_ASSERTION_HEADER: assertion}) == InfrastructureErrorType.OAUTH_ERROR


async def test_a_forged_signature_is_rejected() -> None:
    assertion = _assertion(ec.generate_private_key(ec.SECP256R1()))

    assert await _refused({IAP_ASSERTION_HEADER: assertion}) == InfrastructureErrorType.OAUTH_ERROR


async def test_an_assertion_without_an_email_claim_is_rejected(signing_key: ec.EllipticCurvePrivateKey) -> None:
    assertion = _assertion(signing_key, email=None)

    assert await _refused({IAP_ASSERTION_HEADER: assertion}) == InfrastructureErrorType.OAUTH_ERROR
