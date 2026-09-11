from contextvars import ContextVar, Token
from dataclasses import dataclass

from library.domain.audit.actor import AuditActor
from library.domain.audit.event import AuditSource


@dataclass
class AuditContext:
    actor: AuditActor | None = None
    source: AuditSource | None = None
    correlation_id: str | None = None
    causation_id: str | None = None
    request_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None


_audit_context: ContextVar[AuditContext | None] = ContextVar("audit_context", default=None)


def init_audit_context() -> Token[AuditContext | None]:
    return _audit_context.set(AuditContext())


def flush_audit_context(*, token: Token[AuditContext | None]) -> None:
    _audit_context.reset(token)


def get_audit_context() -> AuditContext | None:
    return _audit_context.get()


def get_actor() -> AuditActor | None:
    context = _audit_context.get()
    return context.actor if context is not None else None


def set_actor(actor: AuditActor, /) -> None:
    context = _audit_context.get()
    if context is not None:
        context.actor = actor


def set_source(source: AuditSource, /) -> None:
    context = _audit_context.get()
    if context is not None:
        context.source = source


def set_correlation_id(correlation_id: str, /) -> None:
    context = _audit_context.get()
    if context is not None:
        context.correlation_id = correlation_id


def set_causation_id(causation_id: str, /) -> None:
    context = _audit_context.get()
    if context is not None:
        context.causation_id = causation_id


def set_request_metadata(*, request_id: str | None, ip_address: str | None, user_agent: str | None) -> None:
    context = _audit_context.get()
    if context is not None:
        context.request_id = request_id
        context.ip_address = ip_address
        context.user_agent = user_agent
