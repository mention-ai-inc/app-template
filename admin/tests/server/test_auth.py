import json
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import Request
from jwt.algorithms import ECAlgorithm

from admin.server import auth
from admin.server.auth import Operator, require_operator
from library.application.audit.context import flush_audit_context, get_actor, init_audit_context
from library.domain.audit.actor import AuditActorType
from library.presentation.errors import PresentationError, PresentationErrorType

AUDIENCE = "/projects/000000000002/global/backendServices/1234567890"
KID = "test-kid"
SUBJECT = "accounts.google.com:12345"
STAFF_EMAIL = "engineer@acme.example.com"


@pytest.fixture
def signing_key() -> ec.EllipticCurvePrivateKey:
    return ec.generate_private_key(ec.SECP256R1())


@pytest.fixture(autouse=True)
def iap_environment(monkeypatch: pytest.MonkeyPatch, signing_key: ec.EllipticCurvePrivateKey) -> None:
    jwk = json.loads(ECAlgorithm.to_jwk(signing_key.public_key()))
    jwk["kid"] = KID
    jwk["alg"] = "ES256"
    signing_keys = {KID: jwk}

    async def fetch_signing_keys() -> dict[str, Any]:
        return signing_keys

    monkeypatch.setattr(auth, "_signing_keys", dict(signing_keys))
    monkeypatch.setattr(auth, "_fetch_signing_keys", fetch_signing_keys)
    monkeypatch.setattr(auth, "_audience", AUDIENCE)
    monkeypatch.setenv("STAFF_ALLOWLIST", STAFF_EMAIL)


def _assertion(
    signing_key: ec.EllipticCurvePrivateKey,
    *,
    email: str | None = STAFF_EMAIL,
    issuer: str = auth.IAP_ISSUER,
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


def _request(assertion: str | None) -> Request:
    headers = [(auth.IAP_ASSERTION_HEADER.encode(), assertion.encode())] if assertion is not None else []
    return Request({"type": "http", "method": "GET", "path": "/", "headers": headers})


async def test_valid_assertion_returns_operator(signing_key: ec.EllipticCurvePrivateKey) -> None:
    operator = await require_operator(_request(_assertion(signing_key)))

    assert operator == Operator(subject=SUBJECT, email=STAFF_EMAIL)


async def test_valid_assertion_sets_operator_actor(signing_key: ec.EllipticCurvePrivateKey) -> None:
    token = init_audit_context()
    try:
        await require_operator(_request(_assertion(signing_key)))
        actor = get_actor()
        assert actor is not None
        assert actor.actor_type == AuditActorType.OPERATOR
        assert actor.actor_email == STAFF_EMAIL
        assert actor.actor_id == SUBJECT
    finally:
        flush_audit_context(token=token)


async def test_missing_assertion_fails_closed() -> None:
    with pytest.raises(PresentationError) as error:
        await require_operator(_request(None))

    assert error.value.error_type == PresentationErrorType.AUTHENTICATION_ERROR


async def test_garbage_assertion_is_rejected() -> None:
    with pytest.raises(PresentationError) as error:
        await require_operator(_request("not-a-jwt"))

    assert error.value.error_type == PresentationErrorType.AUTHENTICATION_ERROR


async def test_wrong_issuer_is_rejected(signing_key: ec.EllipticCurvePrivateKey) -> None:
    assertion = _assertion(signing_key, issuer="https://accounts.google.com")

    with pytest.raises(PresentationError) as error:
        await require_operator(_request(assertion))

    assert error.value.error_type == PresentationErrorType.AUTHENTICATION_ERROR


async def test_wrong_audience_is_rejected(signing_key: ec.EllipticCurvePrivateKey) -> None:
    assertion = _assertion(signing_key, audience="/projects/999/global/backendServices/1")

    with pytest.raises(PresentationError) as error:
        await require_operator(_request(assertion))

    assert error.value.error_type == PresentationErrorType.AUTHENTICATION_ERROR


async def test_expired_assertion_is_rejected(signing_key: ec.EllipticCurvePrivateKey) -> None:
    assertion = _assertion(signing_key, expires_in_seconds=-60)

    with pytest.raises(PresentationError) as error:
        await require_operator(_request(assertion))

    assert error.value.error_type == PresentationErrorType.AUTHENTICATION_ERROR


async def test_unknown_signing_key_is_rejected(signing_key: ec.EllipticCurvePrivateKey) -> None:
    assertion = _assertion(signing_key, kid="unknown-kid")

    with pytest.raises(PresentationError) as error:
        await require_operator(_request(assertion))

    assert error.value.error_type == PresentationErrorType.AUTHENTICATION_ERROR


async def test_forged_signature_is_rejected() -> None:
    forging_key = ec.generate_private_key(ec.SECP256R1())
    assertion = _assertion(forging_key)

    with pytest.raises(PresentationError) as error:
        await require_operator(_request(assertion))

    assert error.value.error_type == PresentationErrorType.AUTHENTICATION_ERROR


async def test_missing_email_claim_is_rejected(signing_key: ec.EllipticCurvePrivateKey) -> None:
    assertion = _assertion(signing_key, email=None)

    with pytest.raises(PresentationError) as error:
        await require_operator(_request(assertion))

    assert error.value.error_type == PresentationErrorType.AUTHENTICATION_ERROR


async def test_unlisted_email_is_denied(signing_key: ec.EllipticCurvePrivateKey) -> None:
    assertion = _assertion(signing_key, email="intruder@example.com")

    with pytest.raises(PresentationError) as error:
        await require_operator(_request(assertion))

    assert error.value.error_type == PresentationErrorType.AUTHORIZATION_ERROR


async def test_empty_allowlist_denies_everyone(
    monkeypatch: pytest.MonkeyPatch, signing_key: ec.EllipticCurvePrivateKey
) -> None:
    monkeypatch.setenv("STAFF_ALLOWLIST", "")
    assertion = _assertion(signing_key)

    with pytest.raises(PresentationError) as error:
        await require_operator(_request(assertion))

    assert error.value.error_type == PresentationErrorType.AUTHORIZATION_ERROR
