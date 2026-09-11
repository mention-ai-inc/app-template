from contextvars import ContextVar, Token
from typing import Any

from library.domain.aggregates import Aggregate
from library.domain.value_objects.users import OrganizationID

type _SnapshotKey = tuple[str, str, str]

_snapshots: ContextVar[dict[_SnapshotKey, Aggregate[Any, Any, Any]] | None] = ContextVar(
    "audit_snapshots", default=None
)


def init_snapshot_context() -> Token[dict[_SnapshotKey, Aggregate[Any, Any, Any]] | None]:
    return _snapshots.set({})


def flush_snapshot_context(*, token: Token[dict[_SnapshotKey, Aggregate[Any, Any, Any]] | None]) -> None:
    _snapshots.reset(token)


def remember(aggregate: Aggregate[Any, Any, Any], /, *, document_id: str) -> None:
    store = _snapshots.get()
    if store is None:
        return

    key = (type(aggregate).__name__, aggregate.organization_id, document_id)
    if key in store:
        return

    store[key] = aggregate.model_copy(deep=True)


def recall(
    aggregate_type: type[Aggregate[Any, Any, Any]], /, *, organization_id: OrganizationID, document_id: str
) -> Aggregate[Any, Any, Any] | None:
    store = _snapshots.get()
    if store is None:
        return None

    return store.get((aggregate_type.__name__, organization_id, document_id))
