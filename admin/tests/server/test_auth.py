import pytest
from fastapi import Request

from admin.server.auth import Operator, require_operator
from library.application.audit.context import flush_audit_context, get_actor, init_audit_context
from library.domain.audit.actor import AuditActorType
from library.presentation.errors import PresentationError, PresentationErrorType
from library.providers.local.operators import LOCAL_OPERATOR_HEADER

STAFF_EMAIL = "engineer@acme.example.com"


@pytest.fixture(autouse=True)
def staff_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STAFF_ALLOWLIST", STAFF_EMAIL)


def _request(operator_email: str | None) -> Request:
    headers = [(LOCAL_OPERATOR_HEADER.encode(), operator_email.encode())] if operator_email is not None else []
    return Request({"type": "http", "method": "GET", "path": "/", "headers": headers})


async def test_an_authenticated_operator_comes_back_identified() -> None:
    operator = await require_operator(_request(STAFF_EMAIL))

    assert operator == Operator(subject=f"local:{STAFF_EMAIL}", email=STAFF_EMAIL)


async def test_an_authenticated_operator_becomes_the_audit_actor() -> None:
    token = init_audit_context()
    try:
        operator = await require_operator(_request(STAFF_EMAIL))
        actor = get_actor()
        assert actor is not None
        assert actor.actor_type == AuditActorType.OPERATOR
        assert actor.actor_email == STAFF_EMAIL
        assert actor.actor_id == operator.subject
    finally:
        flush_audit_context(token=token)


async def test_an_unauthenticated_caller_fails_closed() -> None:
    with pytest.raises(PresentationError) as error:
        await require_operator(_request(None))

    assert error.value.error_type == PresentationErrorType.AUTHENTICATION_ERROR


async def test_an_unlisted_email_is_denied() -> None:
    with pytest.raises(PresentationError) as error:
        await require_operator(_request("intruder@example.com"))

    assert error.value.error_type == PresentationErrorType.AUTHORIZATION_ERROR


async def test_an_empty_allowlist_denies_everyone(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STAFF_ALLOWLIST", "")

    with pytest.raises(PresentationError) as error:
        await require_operator(_request(STAFF_EMAIL))

    assert error.value.error_type == PresentationErrorType.AUTHORIZATION_ERROR
