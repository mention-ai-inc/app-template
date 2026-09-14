from datetime import UTC, datetime

import pytest

from library.application.errors import ApplicationError, ApplicationErrorType
from library.application.ports.documents import ArrayUnion, DocumentID, Increment, QueryFilter, SortBy
from library.domain.entities import Entity
from library.domain.value_objects.core import IDValueObject
from library.infrastructure.errors import InfrastructureError
from library.providers.local.database import LocalDatabase
from library.providers.local.documents import LocalDocumentStore
from library.providers.local.unit_of_work import get_current_local_transaction, local_unit_of_work


class WidgetID(IDValueObject):
    PREFIX = "wid_"


class PartID(IDValueObject):
    PREFIX = "part_"


class PartitionKey(IDValueObject):
    PREFIX = "org_"


class Part(Entity[PartID]):
    label: str


class Widget(Entity[WidgetID]):
    name: str
    size: int
    made_at: datetime
    parts: list[Part] = []


@pytest.fixture(autouse=True)
def _empty_database() -> None:
    LocalDatabase.clear()


def _store() -> LocalDocumentStore[Widget, PartitionKey]:
    return LocalDocumentStore(collection="widgets", model=Widget, partition_key_type=PartitionKey, service="notes")


def _widget(*, name: str = "a", size: int = 1, parts: list[Part] | None = None) -> Widget:
    return Widget(id=WidgetID(), name=name, size=size, made_at=datetime(2026, 1, 1, tzinfo=UTC), parts=parts or [])


class TestPartitioning:
    def test_collection_id_is_scoped_inside_a_partition(self) -> None:
        store = _store()
        partition_key = PartitionKey()

        with store.connect_to_partition(partition_key) as scoped:
            assert scoped.collection_id == f"notes_{partition_key}_widgets"
            assert scoped.active_partition_key == partition_key

        assert store.collection_id == "notes_widgets"

    def test_active_partition_key_outside_a_partition_raises(self) -> None:
        with pytest.raises(InfrastructureError):
            _store().active_partition_key

    async def test_partitions_do_not_see_each_others_documents(self) -> None:
        store = _store()
        widget = _widget()
        left, right = PartitionKey(), PartitionKey()

        with store.connect_to_partition(left) as scoped:
            await scoped.set(document_id=store.to_document_id(widget.id), document_data=widget)

        with store.connect_to_partition(right) as scoped:
            assert await scoped.exists(document_id=store.to_document_id(widget.id)) is False


class TestRoundTrip:
    async def test_a_document_comes_back_as_it_went_in(self) -> None:
        store = _store()
        widget = _widget(name="hammer", size=7)

        await store.set(document_id=store.to_document_id(widget.id), document_data=widget)
        read = await store.get(document_id=store.to_document_id(widget.id))

        assert read == widget

    async def test_a_missing_document_raises_resource_not_found(self) -> None:
        with pytest.raises(ApplicationError) as exc_info:
            await _store().get(document_id=DocumentID("nope"))

        assert exc_info.value.error_type == ApplicationErrorType.RESOURCE_NOT_FOUND

    async def test_get_many_preserves_request_order(self) -> None:
        store = _store()
        widgets = [_widget(name=name) for name in ("a", "b", "c")]
        for widget in widgets:
            await store.set(document_id=store.to_document_id(widget.id), document_data=widget)

        read = await store.get_many(document_ids=[store.to_document_id(w.id) for w in reversed(widgets)])

        assert [w.name for w in read] == ["c", "b", "a"]

    async def test_get_many_can_ignore_missing_documents(self) -> None:
        store = _store()
        widget = _widget()
        await store.set(document_id=store.to_document_id(widget.id), document_data=widget)

        read = await store.get_many(
            document_ids=[store.to_document_id(widget.id), DocumentID("absent")], ignore_missing=True
        )

        assert len(read) == 1


class TestSubcollections:
    async def test_subentities_survive_a_round_trip(self) -> None:
        store = _store()
        widget = _widget(parts=[Part(id=PartID(), label="head"), Part(id=PartID(), label="handle")])

        await store.set(document_id=store.to_document_id(widget.id), document_data=widget)
        read = await store.get(document_id=store.to_document_id(widget.id))

        assert sorted(part.label for part in read.parts) == ["handle", "head"]

    async def test_a_removed_subentity_is_pruned_on_the_next_write(self) -> None:
        store = _store()
        kept, dropped = Part(id=PartID(), label="kept"), Part(id=PartID(), label="dropped")
        widget = _widget(parts=[kept, dropped])
        document_id = store.to_document_id(widget.id)
        await store.set(document_id=document_id, document_data=widget)

        widget.parts = [kept]
        await store.set(document_id=document_id, document_data=widget)
        read = await store.get(document_id=document_id)

        assert [part.label for part in read.parts] == ["kept"]

    async def test_a_shallow_query_returns_counts_but_not_subentities(self) -> None:
        store = _store()
        widget = _widget(parts=[Part(id=PartID(), label="head")])
        await store.set(document_id=store.to_document_id(widget.id), document_data=widget)

        result = await store.query()

        assert result.entities[0].parts == []
        assert result.subcollection_counts == [{"parts": 1}]

    async def test_a_deep_query_returns_the_subentities(self) -> None:
        store = _store()
        widget = _widget(parts=[Part(id=PartID(), label="head")])
        await store.set(document_id=store.to_document_id(widget.id), document_data=widget)

        result = await store.query(mode="deep")

        assert [part.label for part in result.entities[0].parts] == ["head"]

    async def test_deleting_a_document_cascades_to_its_subentities(self) -> None:
        store = _store()
        widget = _widget(parts=[Part(id=PartID(), label="head")])
        document_id = store.to_document_id(widget.id)
        await store.set(document_id=document_id, document_data=widget)

        await store.delete(document_id=document_id)

        assert LocalDatabase.read_all(collection_id=f"notes_widgets/{document_id}/parts") == {}


class TestQuerying:
    async def _seed(self) -> LocalDocumentStore[Widget, PartitionKey]:
        store = _store()
        for name, size in (("a", 1), ("b", 2), ("c", 3)):
            widget = _widget(name=name, size=size)
            await store.set(document_id=store.to_document_id(widget.id), document_data=widget)
        return store

    async def test_equality_filters(self) -> None:
        store = await self._seed()

        result = await store.query(filters=[QueryFilter(field="name", operator="==", value="b")])

        assert [w.name for w in result.entities] == ["b"]

    async def test_comparison_filters(self) -> None:
        store = await self._seed()

        result = await store.query(filters=[QueryFilter(field="size", operator=">=", value=2)])

        assert sorted(w.name for w in result.entities) == ["b", "c"]

    async def test_in_filters(self) -> None:
        store = await self._seed()

        result = await store.query(filters=[QueryFilter(field="name", operator="in", value=["a", "c"])])

        assert sorted(w.name for w in result.entities) == ["a", "c"]

    async def test_sorting_descending(self) -> None:
        store = await self._seed()

        result = await store.query(sort_by=SortBy(field="size", direction="DESCENDING"))

        assert [w.name for w in result.entities] == ["c", "b", "a"]

    async def test_limit_reports_more_results(self) -> None:
        store = await self._seed()

        result = await store.query(sort_by=SortBy(field="size", direction="ASCENDING"), limit=2)

        assert [w.name for w in result.entities] == ["a", "b"]
        assert result.has_more is True

    async def test_limit_that_covers_everything_reports_no_more(self) -> None:
        store = await self._seed()

        result = await store.query(limit=3)

        assert result.has_more is False

    async def test_count_ignores_documents_that_do_not_match(self) -> None:
        store = await self._seed()

        assert await store.count(filters=[QueryFilter(field="size", operator="<", value=3)]) == 2

    async def test_query_one_returns_none_when_nothing_matches(self) -> None:
        store = await self._seed()

        assert await store.query_one(filters=[QueryFilter(field="name", operator="==", value="z")]) is None

    async def test_query_one_refuses_an_ambiguous_result(self) -> None:
        store = await self._seed()

        with pytest.raises(InfrastructureError):
            await store.query_one(filters=[QueryFilter(field="size", operator=">", value=0)])


class TestFieldMutations:
    async def test_increment_adds_to_the_stored_value(self) -> None:
        store = _store()
        widget = _widget(size=5)
        document_id = store.to_document_id(widget.id)
        await store.set(document_id=document_id, document_data=widget)

        await store.mutate_fields(document_id=document_id, field_updates={"size": Increment(3)})

        assert (await store.get(document_id=document_id)).size == 8

    async def test_array_union_does_not_duplicate_existing_members(self) -> None:
        store = _store()
        widget = _widget()
        document_id = store.to_document_id(widget.id)
        await store.set(document_id=document_id, document_data=widget)
        await store.mutate_fields(document_id=document_id, field_updates={"tags": ArrayUnion(["x"])})

        await store.mutate_fields(document_id=document_id, field_updates={"tags": ArrayUnion(["x", "y"])})

        stored = LocalDatabase.read(collection_id=store.collection_id, document_id=document_id)
        assert stored is not None
        assert stored.data["tags"] == ["x", "y"]

    async def test_field_set_replaces_one_value(self) -> None:
        store = _store()
        widget = _widget(name="before")
        document_id = store.to_document_id(widget.id)
        await store.set(document_id=document_id, document_data=widget)

        await store.field_set(document_id=document_id, field="name", value="after")

        assert (await store.get(document_id=document_id)).name == "after"


class TestTransactions:
    async def test_writes_are_invisible_until_the_block_closes(self) -> None:
        store = _store()
        widget = _widget()
        document_id = store.to_document_id(widget.id)

        async with local_unit_of_work():
            await store.set(document_id=document_id, document_data=widget, uow=get_current_local_transaction())
            assert await store.exists(document_id=document_id) is False

        assert await store.exists(document_id=document_id) is True

    async def test_a_failed_block_writes_nothing(self) -> None:
        store = _store()
        widget = _widget()
        document_id = store.to_document_id(widget.id)

        with pytest.raises(RuntimeError):
            async with local_unit_of_work():
                await store.set(document_id=document_id, document_data=widget, uow=get_current_local_transaction())
                raise RuntimeError("use case failed")

        assert await store.exists(document_id=document_id) is False

    async def test_reading_after_writing_inside_a_block_is_refused(self) -> None:
        store = _store()
        widget = _widget()

        with pytest.raises(InfrastructureError):
            async with local_unit_of_work():
                uow = get_current_local_transaction()
                await store.set(document_id=store.to_document_id(widget.id), document_data=widget, uow=uow)
                await store.get(document_id=store.to_document_id(widget.id), uow=uow)

    async def test_a_document_changed_since_it_was_read_aborts_the_commit(self) -> None:
        store = _store()
        widget = _widget(name="original")
        document_id = store.to_document_id(widget.id)
        await store.set(document_id=document_id, document_data=widget)

        with pytest.raises(ApplicationError) as exc_info:
            async with local_unit_of_work():
                uow = get_current_local_transaction()
                read = await store.get(document_id=document_id, uow=uow)
                await store.field_set(document_id=document_id, field="name", value="someone else")
                read.name = "mine"
                await store.set(document_id=document_id, document_data=read, uow=uow)

        assert exc_info.value.error_type == ApplicationErrorType.TRANSACTION_CONFLICT

    async def test_an_uncontended_read_then_write_commits(self) -> None:
        store = _store()
        widget = _widget(name="original")
        document_id = store.to_document_id(widget.id)
        await store.set(document_id=document_id, document_data=widget)

        async with local_unit_of_work():
            uow = get_current_local_transaction()
            read = await store.get(document_id=document_id, uow=uow)
            read.name = "updated"
            await store.set(document_id=document_id, document_data=read, uow=uow)

        assert (await store.get(document_id=document_id)).name == "updated"

    def test_asking_for_a_transaction_outside_a_block_raises(self) -> None:
        with pytest.raises(InfrastructureError):
            get_current_local_transaction()
