from library.application.audit.context import (
    flush_audit_context,
    get_actor,
    init_audit_context,
    set_actor,
    set_correlation_id,
)
from library.domain.audit.actor import AuditActor


def test_actor_is_none_without_an_initialized_context() -> None:
    assert get_actor() is None


def test_set_actor_is_readable_within_the_context() -> None:
    token = init_audit_context()
    actor = AuditActor.system()

    set_actor(actor)

    assert get_actor() == actor
    flush_audit_context(token=token)


def test_set_actor_is_a_noop_without_an_initialized_context() -> None:
    set_actor(AuditActor.system())

    assert get_actor() is None


def test_flush_restores_the_enclosing_context() -> None:
    outer_token = init_audit_context()
    set_actor(AuditActor.system())

    inner_token = init_audit_context()
    assert get_actor() is None

    set_correlation_id("inner")
    flush_audit_context(token=inner_token)

    assert get_actor() == AuditActor.system()
    flush_audit_context(token=outer_token)
