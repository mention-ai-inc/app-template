from collections.abc import Generator

import pytest
from pydantic import ConfigDict

from library.domain.aggregates import Aggregate
from library.domain.commands.base import CommandPayload
from library.domain.entities import Entity
from library.domain.events.base import EventPayload
from library.domain.value_objects.common import Service
from library.domain.value_objects.core import IDValueObject
from library.domain.value_objects.users import OrganizationID
from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType
from library.infrastructure.repository import Repository
from library.providers.local.provider import PROVIDER as LOCAL_PROVIDER
from library.providers.registry import reset_cloud_provider, set_cloud_provider


class _AggId(IDValueObject):
    PREFIX = "agg_"


class _SampleEvent(EventPayload):
    organization_id: OrganizationID


class _SampleCommand(CommandPayload):
    SERVICE = Service.NOTES
    organization_id: OrganizationID

    model_config = ConfigDict(frozen=True)


class _PlainAggregate(Aggregate[_AggId, _SampleEvent, _SampleCommand]):
    name: str = ""


class _SubId(IDValueObject):
    PREFIX = "sub_"


class _SubItem(Entity[_SubId]):
    pass


class _AggregateWithSubcollection(Aggregate[_AggId, _SampleEvent, _SampleCommand]):
    items: list[_SubItem] = []


class _OverridingDeleteRepository(Repository[_PlainAggregate, _AggId, _SampleEvent, _SampleCommand]):
    def __init__(self) -> None:
        super().__init__(aggregate=_PlainAggregate, identity_type=_AggId)

    async def delete(self, aggregate_id: _AggId, /, *, organization_id: OrganizationID) -> None:
        await super().delete(aggregate_id, organization_id=organization_id)


@pytest.fixture(autouse=True)
def _local_provider(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:  # pyright: ignore[reportUnusedFunction]
    monkeypatch.setenv("SERVICE", Service.NOTES.value)
    set_cloud_provider(LOCAL_PROVIDER)
    yield
    reset_cloud_provider()


async def test_quick_delete_refuses_when_subclass_overrides_delete() -> None:
    repo = _OverridingDeleteRepository()

    with pytest.raises(InfrastructureError) as exc_info:
        await repo.quick_delete(_AggId(), organization_id=__org())

    assert exc_info.value.error_type == InfrastructureErrorType.ENVIRONMENT_ERROR


async def test_quick_delete_refuses_when_aggregate_has_subcollections() -> None:
    repo = Repository[_AggregateWithSubcollection, _AggId, _SampleEvent, _SampleCommand](
        aggregate=_AggregateWithSubcollection, identity_type=_AggId
    )

    with pytest.raises(InfrastructureError) as exc_info:
        await repo.quick_delete(_AggId(), organization_id=__org())

    assert exc_info.value.error_type == InfrastructureErrorType.ENVIRONMENT_ERROR


def __org() -> OrganizationID:
    return OrganizationID("org_test")
