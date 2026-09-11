import pytest
from pydantic import ConfigDict

from library._testutils.repository import InMemoryRepository
from library._testutils.unit_of_work import FakeUnitOfWork, in_uow
from library.application.errors import ApplicationError, ApplicationErrorType
from library.domain.aggregates import Aggregate
from library.domain.commands.base import CommandPayload
from library.domain.events.base import EventPayload
from library.domain.services import ChangeSet
from library.domain.value_objects.common import Service
from library.domain.value_objects.core import IDValueObject
from library.domain.value_objects.users import OrganizationID
from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType


class _SampleId(IDValueObject):
    PREFIX = "sample_"


class _SampleEvent(EventPayload):
    organization_id: OrganizationID
    note: str


class _SampleCommand(CommandPayload):
    SERVICE = Service.NOTES
    organization_id: OrganizationID
    instruction: str

    model_config = ConfigDict(frozen=True)


class _SampleAggregate(Aggregate[_SampleId, _SampleEvent, _SampleCommand]):
    name: str = ""


def _org() -> OrganizationID:
    return OrganizationID("org_123")


def _other_org() -> OrganizationID:
    return OrganizationID("org_456")


def _aggregate(name: str = "thing") -> _SampleAggregate:
    return _SampleAggregate(id=_SampleId(), organization_id=_org(), name=name)


async def test_get_outside_unit_of_work_raises_environment_error() -> None:
    repo = InMemoryRepository[_SampleAggregate, _SampleId, _SampleEvent, _SampleCommand]()
    aggregate = _aggregate()
    await repo.seed(aggregate, organization_id=_org())

    with pytest.raises(InfrastructureError) as exc_info:
        await repo.get(aggregate.id, organization_id=_org())

    assert exc_info.value.error_type == InfrastructureErrorType.ENVIRONMENT_ERROR


async def test_save_then_get_roundtrips_the_aggregate() -> None:
    repo = InMemoryRepository[_SampleAggregate, _SampleId, _SampleEvent, _SampleCommand]()
    aggregate = _aggregate("hello")

    async with in_uow():
        await repo.save(aggregate)
    async with in_uow():
        fetched = await repo.get(aggregate.id, organization_id=_org())

    assert fetched == aggregate
    assert fetched is not aggregate


async def test_save_marks_aggregate_as_published_clearing_pending_events() -> None:
    repo = InMemoryRepository[_SampleAggregate, _SampleId, _SampleEvent, _SampleCommand]()
    aggregate = _aggregate()
    aggregate.add_event(_SampleEvent(organization_id=_org(), note="first"))

    async with in_uow():
        await repo.save(aggregate)

    assert aggregate.events == []
    assert len(repo.published_events) == 1


async def test_save_twice_does_not_republish_already_recorded_events() -> None:
    repo = InMemoryRepository[_SampleAggregate, _SampleId, _SampleEvent, _SampleCommand]()
    aggregate = _aggregate()
    aggregate.add_event(_SampleEvent(organization_id=_org(), note="once"))

    async with in_uow():
        await repo.save(aggregate)
        await repo.save(aggregate)

    assert len(repo.published_events) == 1


async def test_seed_does_not_leak_pending_events_into_a_later_save() -> None:
    repo = InMemoryRepository[_SampleAggregate, _SampleId, _SampleEvent, _SampleCommand]()
    aggregate = _aggregate()
    aggregate.add_event(_SampleEvent(organization_id=_org(), note="created"))
    await repo.seed(aggregate, organization_id=_org())

    async with in_uow():
        fetched = await repo.get(aggregate.id, organization_id=_org())
        fetched.add_event(_SampleEvent(organization_id=_org(), note="updated"))
        await repo.save(fetched)

    assert [event.payload.note for event in repo.published_events] == ["updated"]


async def test_seed_clears_pending_events_so_seeded_aggregate_equals_a_read_back_copy() -> None:
    repo = InMemoryRepository[_SampleAggregate, _SampleId, _SampleEvent, _SampleCommand]()
    aggregate = _aggregate()
    aggregate.add_event(_SampleEvent(organization_id=_org(), note="created"))

    await repo.seed(aggregate, organization_id=_org())

    assert aggregate.events == []
    fetched = await repo.quick_get(aggregate.id, organization_id=_org())
    assert fetched == aggregate


async def test_get_missing_raises_resource_not_found() -> None:
    repo = InMemoryRepository[_SampleAggregate, _SampleId, _SampleEvent, _SampleCommand]()

    with pytest.raises(ApplicationError) as exc_info:
        async with in_uow():
            await repo.get(_SampleId(), organization_id=_org())

    assert exc_info.value.error_type == ApplicationErrorType.RESOURCE_NOT_FOUND


async def test_exists_reflects_save() -> None:
    repo = InMemoryRepository[_SampleAggregate, _SampleId, _SampleEvent, _SampleCommand]()
    aggregate = _aggregate()

    assert await repo.exists(aggregate.id, organization_id=_org()) is False

    async with in_uow():
        await repo.save(aggregate)

    assert await repo.exists(aggregate.id, organization_id=_org()) is True


async def test_list_ids_returns_only_current_organization() -> None:
    repo = InMemoryRepository[_SampleAggregate, _SampleId, _SampleEvent, _SampleCommand]()
    a = _aggregate()
    b = _SampleAggregate(id=_SampleId(), organization_id=_other_org(), name="other")
    async with in_uow():
        await repo.save(a)
        await repo.save(b)

    ids = await repo.list_ids(organization_id=_org())

    assert ids == [a.id]


async def test_get_many_returns_in_request_order() -> None:
    repo = InMemoryRepository[_SampleAggregate, _SampleId, _SampleEvent, _SampleCommand]()
    a = _aggregate("a")
    b = _aggregate("b")
    async with in_uow():
        await repo.save(a)
        await repo.save(b)

    async with in_uow():
        results = await repo.get_many([b.id, a.id], organization_id=_org())

    assert [agg.name for agg in results] == ["b", "a"]


async def test_get_all_returns_only_current_organization() -> None:
    repo = InMemoryRepository[_SampleAggregate, _SampleId, _SampleEvent, _SampleCommand]()
    a = _aggregate("a")
    b = _SampleAggregate(id=_SampleId(), organization_id=_other_org(), name="b")
    async with in_uow():
        await repo.save(a)
        await repo.save(b)

    async with in_uow():
        results = await repo.get_all(organization_id=_org())

    assert [agg.name for agg in results] == ["a"]


async def test_delete_removes_the_aggregate() -> None:
    repo = InMemoryRepository[_SampleAggregate, _SampleId, _SampleEvent, _SampleCommand]()
    aggregate = _aggregate()
    async with in_uow():
        await repo.save(aggregate)
        await repo.delete(aggregate.id, organization_id=_org())

    assert await repo.exists(aggregate.id, organization_id=_org()) is False


async def test_save_captures_events_into_published_events() -> None:
    repo = InMemoryRepository[_SampleAggregate, _SampleId, _SampleEvent, _SampleCommand]()
    aggregate = _aggregate()
    aggregate.add_event(_SampleEvent(organization_id=_org(), note="something happened"))

    async with in_uow():
        await repo.save(aggregate)

    assert len(repo.published_events) == 1
    assert repo.published_events[0].payload.note == "something happened"


async def test_save_captures_commands_into_published_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SERVICE", Service.NOTES.value)
    repo = InMemoryRepository[_SampleAggregate, _SampleId, _SampleEvent, _SampleCommand]()
    aggregate = _aggregate()
    aggregate.add_command(_SampleCommand(organization_id=_org(), instruction="do the thing"))

    async with in_uow():
        await repo.save(aggregate)

    assert len(repo.published_commands) == 1
    assert repo.published_commands[0].payload.instruction == "do the thing"


async def test_apply_changeset_persists_created_updated_and_deletes() -> None:
    repo = InMemoryRepository[_SampleAggregate, _SampleId, _SampleEvent, _SampleCommand]()
    existing = _aggregate("existing")
    created = _aggregate("created")
    updated = _SampleAggregate(id=existing.id, organization_id=_org(), name="updated")
    to_delete = _aggregate("delete-me")
    async with in_uow():
        await repo.save(existing)
        await repo.save(to_delete)

    changeset = ChangeSet[_SampleAggregate, _SampleId, _SampleEvent](
        created=[created],
        updated=[updated],
        deleted=[to_delete.id],
    )

    async with in_uow():
        await repo.apply_changeset(changeset, organization_id=_org())

    assert (await repo.quick_get(created.id, organization_id=_org())).name == "created"
    assert (await repo.quick_get(existing.id, organization_id=_org())).name == "updated"
    assert await repo.exists(to_delete.id, organization_id=_org()) is False


async def test_apply_changeset_records_events_into_published_events() -> None:
    repo = InMemoryRepository[_SampleAggregate, _SampleId, _SampleEvent, _SampleCommand]()
    payload = _SampleEvent(organization_id=_org(), note="from changeset")

    changeset = ChangeSet[_SampleAggregate, _SampleId, _SampleEvent](events=[payload])

    async with in_uow():
        await repo.apply_changeset(changeset, organization_id=_org())

    assert len(repo.published_events) == 1
    assert repo.published_events[0].payload is payload


async def test_read_after_write_inside_unit_of_work_raises() -> None:
    repo = InMemoryRepository[_SampleAggregate, _SampleId, _SampleEvent, _SampleCommand]()
    first = _aggregate("first")
    second = _aggregate("second")
    await repo.seed(second, organization_id=_org())
    unit_of_work = FakeUnitOfWork()

    with pytest.raises(InfrastructureError) as exc_info:
        async with unit_of_work():
            await repo.save(first)
            await repo.get(second.id, organization_id=_org())

    assert exc_info.value.error_type == InfrastructureErrorType.CLOUD_ERROR


async def test_reads_before_writes_inside_unit_of_work_are_allowed() -> None:
    repo = InMemoryRepository[_SampleAggregate, _SampleId, _SampleEvent, _SampleCommand]()
    existing = _aggregate("existing")
    await repo.seed(existing, organization_id=_org())

    async with in_uow():
        fetched = await repo.get(existing.id, organization_id=_org())
        fetched.name = "mutated"
        await repo.save(fetched)

    assert (await repo.quick_get(existing.id, organization_id=_org())).name == "mutated"


async def test_reads_after_writes_in_separate_unit_of_work_blocks_are_allowed() -> None:
    repo = InMemoryRepository[_SampleAggregate, _SampleId, _SampleEvent, _SampleCommand]()
    aggregate = _aggregate("thing")

    async with in_uow():
        await repo.save(aggregate)

    async with in_uow():
        fetched = await repo.get(aggregate.id, organization_id=_org())

    assert fetched.name == "thing"


async def test_quick_delete_removes_the_aggregate_outside_unit_of_work() -> None:
    repo = InMemoryRepository[_SampleAggregate, _SampleId, _SampleEvent, _SampleCommand]()
    aggregate = _aggregate()
    await repo.seed(aggregate, organization_id=_org())

    await repo.quick_delete(aggregate.id, organization_id=_org())

    assert await repo.exists(aggregate.id, organization_id=_org()) is False


async def test_quick_delete_refuses_when_subclass_overrides_delete() -> None:
    # A stub that mirrors production's event-publishing delete override must NOT be quick_delete-able,
    # because quick_delete bypasses the override and would silently drop the deletion event.
    class _OverridingRepository(InMemoryRepository[_SampleAggregate, _SampleId, _SampleEvent, _SampleCommand]):
        async def delete(self, aggregate_id: _SampleId, /, *, organization_id: OrganizationID) -> None:
            await super().delete(aggregate_id, organization_id=organization_id)

    repo = _OverridingRepository()
    aggregate = _aggregate()
    await repo.seed(aggregate, organization_id=_org())

    with pytest.raises(InfrastructureError) as exc_info:
        await repo.quick_delete(aggregate.id, organization_id=_org())

    assert exc_info.value.error_type == InfrastructureErrorType.ENVIRONMENT_ERROR


async def test_quick_get_works_outside_unit_of_work() -> None:
    repo = InMemoryRepository[_SampleAggregate, _SampleId, _SampleEvent, _SampleCommand]()
    aggregate = _aggregate("thing")

    async with in_uow():
        await repo.save(aggregate)
    fetched = await repo.quick_get(aggregate.id, organization_id=_org())

    assert fetched.name == "thing"


async def test_two_organizations_are_isolated() -> None:
    repo = InMemoryRepository[_SampleAggregate, _SampleId, _SampleEvent, _SampleCommand]()
    a = _aggregate("a")
    b = _SampleAggregate(id=a.id, organization_id=_other_org(), name="b")
    async with in_uow():
        await repo.save(a)
        await repo.save(b)

    async with in_uow():
        fetched_in_org = await repo.get(a.id, organization_id=_org())
        fetched_in_other = await repo.get(a.id, organization_id=_other_org())

    assert fetched_in_org.name == "a"
    assert fetched_in_other.name == "b"
