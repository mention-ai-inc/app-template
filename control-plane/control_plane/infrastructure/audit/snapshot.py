from collections.abc import Mapping
from contextvars import ContextVar, Token
from typing import Any, Protocol, Self, cast

from control_plane.domain.value_objects.users import OrganizationID


class ISnapshottable(Protocol):
    @property
    def organization_id(self) -> OrganizationID: ...

    def model_copy(self, *, update: Mapping[str, Any] | None = None, deep: bool = False) -> Self: ...


type _SnapshotKey = tuple[str, str, str]

_snapshots: ContextVar[dict[_SnapshotKey, ISnapshottable] | None] = ContextVar("audit_snapshots", default=None)


def init_snapshot_context() -> Token[dict[_SnapshotKey, ISnapshottable] | None]:
    return _snapshots.set({})


def flush_snapshot_context(*, token: Token[dict[_SnapshotKey, ISnapshottable] | None]) -> None:
    _snapshots.reset(token)


def remember(aggregate: ISnapshottable, /, *, document_id: str) -> None:
    store = _snapshots.get()
    if store is None:
        return

    key = (type(aggregate).__name__, aggregate.organization_id, document_id)
    if key in store:
        return

    store[key] = aggregate.model_copy(deep=True)


def recall[SnapshotT: ISnapshottable](
    aggregate_type: type[SnapshotT], /, *, organization_id: OrganizationID, document_id: str
) -> SnapshotT | None:
    store = _snapshots.get()
    if store is None:
        return None

    return cast(SnapshotT | None, store.get((aggregate_type.__name__, organization_id, document_id)))
