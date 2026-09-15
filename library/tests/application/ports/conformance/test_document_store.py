from collections.abc import Sequence

import pytest

from library.application.errors import ApplicationError, ApplicationErrorType
from library.application.ports.documents import (
    ArrayRemove,
    ArrayUnion,
    DocumentID,
    Increment,
    Primitive,
    QueryFilter,
    QueryOperator,
    SortBy,
)
from library.application.ports.provider import ICloudProvider
from library.infrastructure.errors import InfrastructureError
from tests.application.ports.conformance.providers import CONFORMANCE_SERVICE
from tests.application.ports.conformance.stores import MainStore, SimpleStore
from tests.infrastructure.persistence.mocks import (
    CompositeSub,
    CompositeSubId,
    IntSub,
    IntSubId,
    MainEntity,
    MainId,
    MockPartitionKey,
    SimpleEntity,
    StringSub,
    StringSubId,
)


async def _store_document(store: SimpleStore, *, name: str) -> DocumentID:
    entity = SimpleEntity(id=MainId(), name=name)
    document_id = store.to_document_id(entity.id)
    await store.set(document_id=document_id, document_data=entity)
    return document_id


async def _seed(store: SimpleStore, names: Sequence[str]) -> dict[str, DocumentID]:
    return {name: await _store_document(store, name=name) for name in names}


class TestCollectionNaming:
    def test_the_collection_id_is_the_service_and_the_collection(self, simple_store: SimpleStore) -> None:
        assert simple_store.collection_id == f"{CONFORMANCE_SERVICE.value}_simple"

    def test_the_collection_id_carries_the_feature_environment(self, provider: ICloudProvider) -> None:
        store = provider.document_store(
            collection="simple",
            model=SimpleEntity,
            partition_key_type=MockPartitionKey,
            service=CONFORMANCE_SERVICE,
            feature_environment="pr7",
        )

        assert store.collection_id == f"pr7{CONFORMANCE_SERVICE.value}_simple"


class TestDocumentIdentifiers:
    def test_a_string_identity_is_used_verbatim(self, simple_store: SimpleStore) -> None:
        entity_id = StringSubId()

        assert simple_store.to_document_id(entity_id) == str(entity_id)

    def test_an_integer_identity_becomes_its_decimal_form(self, simple_store: SimpleStore) -> None:
        assert simple_store.to_document_id(IntSubId(7)) == "7"

    def test_a_model_identity_becomes_a_reversible_encoding(self, simple_store: SimpleStore) -> None:
        entity_id = CompositeSubId(org="acme", user="nash")

        document_id = simple_store.to_document_id(entity_id)

        assert CompositeSubId.from_id(id=document_id) == entity_id


class TestPartitioning:
    def test_the_collection_id_is_scoped_inside_a_partition(self, simple_store: SimpleStore) -> None:
        partition_key = MockPartitionKey()

        with simple_store.connect_to_partition(partition_key) as scoped:
            assert scoped.collection_id == f"{CONFORMANCE_SERVICE.value}_{partition_key}_simple"
            assert scoped.active_partition_key == partition_key

        assert simple_store.collection_id == f"{CONFORMANCE_SERVICE.value}_simple"

    def test_asking_for_the_partition_key_outside_a_partition_raises(self, simple_store: SimpleStore) -> None:
        with pytest.raises(InfrastructureError):
            simple_store.active_partition_key

    async def test_partitions_do_not_see_each_others_documents(self, simple_store: SimpleStore) -> None:
        left, right = MockPartitionKey(), MockPartitionKey()

        with simple_store.connect_to_partition(left) as scoped:
            document_id = await _store_document(scoped, name="left")

        with simple_store.connect_to_partition(right) as scoped:
            assert await scoped.exists(document_id=document_id) is False

        with simple_store.connect_to_partition(left) as scoped:
            assert await scoped.exists(document_id=document_id) is True


class TestRoundTrip:
    async def test_a_document_comes_back_as_it_went_in(self, simple_store: SimpleStore) -> None:
        entity = SimpleEntity(id=MainId(), name="hammer")

        await simple_store.set(document_id=simple_store.to_document_id(entity.id), document_data=entity)
        read = await simple_store.get(document_id=simple_store.to_document_id(entity.id))

        assert read == entity

    async def test_a_missing_document_raises_resource_not_found(self, simple_store: SimpleStore) -> None:
        with pytest.raises(ApplicationError) as exc_info:
            await simple_store.get(document_id=DocumentID("absent"))

        assert exc_info.value.error_type == ApplicationErrorType.RESOURCE_NOT_FOUND

    async def test_get_many_preserves_the_requested_order(self, simple_store: SimpleStore) -> None:
        seeded = await _seed(simple_store, ("a", "b", "c"))

        read = await simple_store.get_many(document_ids=[seeded["c"], seeded["a"], seeded["b"]])

        assert [entity.name for entity in read] == ["c", "a", "b"]

    async def test_get_many_can_ignore_missing_documents(self, simple_store: SimpleStore) -> None:
        seeded = await _seed(simple_store, ("a",))

        read = await simple_store.get_many(document_ids=[seeded["a"], DocumentID("absent")], ignore_missing=True)

        assert [entity.name for entity in read] == ["a"]

    async def test_get_many_refuses_a_missing_document_by_default(self, simple_store: SimpleStore) -> None:
        seeded = await _seed(simple_store, ("a",))

        with pytest.raises(ApplicationError) as exc_info:
            await simple_store.get_many(document_ids=[seeded["a"], DocumentID("absent")])

        assert exc_info.value.error_type == ApplicationErrorType.RESOURCE_NOT_FOUND

    async def test_exists_reports_whether_the_document_is_there(self, simple_store: SimpleStore) -> None:
        seeded = await _seed(simple_store, ("a",))

        assert await simple_store.exists(document_id=seeded["a"]) is True
        assert await simple_store.exists(document_id=DocumentID("absent")) is False

    async def test_delete_removes_the_document(self, simple_store: SimpleStore) -> None:
        seeded = await _seed(simple_store, ("a",))

        await simple_store.delete(document_id=seeded["a"])

        assert await simple_store.exists(document_id=seeded["a"]) is False


class TestFieldWrites:
    async def test_field_set_replaces_one_value(self, simple_store: SimpleStore) -> None:
        seeded = await _seed(simple_store, ("before",))

        await simple_store.field_set(document_id=seeded["before"], field="name", value="after")

        assert (await simple_store.get(document_id=seeded["before"])).name == "after"

    async def test_set_merge_leaves_untouched_fields_alone(self, simple_store: SimpleStore) -> None:
        seeded = await _seed(simple_store, ("original",))

        await simple_store.set_merge(document_id=seeded["original"], document_data={"counter": 1})

        assert (await simple_store.get(document_id=seeded["original"])).name == "original"

    async def test_set_merge_overwrites_the_fields_it_is_given(self, simple_store: SimpleStore) -> None:
        seeded = await _seed(simple_store, ("original",))

        await simple_store.set_merge(document_id=seeded["original"], document_data={"name": "merged"})

        assert (await simple_store.get(document_id=seeded["original"])).name == "merged"

    async def test_increment_accumulates_onto_the_stored_value(self, simple_store: SimpleStore) -> None:
        seeded = await _seed(simple_store, ("counted",))

        await simple_store.mutate_fields(document_id=seeded["counted"], field_updates={"counter": Increment(3)})
        await simple_store.mutate_fields(document_id=seeded["counted"], field_updates={"counter": Increment(4)})

        assert await simple_store.count(filters=[QueryFilter(field="counter", operator="==", value=7)]) == 1

    async def test_array_union_does_not_duplicate_existing_members(self, simple_store: SimpleStore) -> None:
        seeded = await _seed(simple_store, ("tagged",))

        await simple_store.mutate_fields(document_id=seeded["tagged"], field_updates={"tags": ArrayUnion(["x"])})
        await simple_store.mutate_fields(document_id=seeded["tagged"], field_updates={"tags": ArrayUnion(["x", "y"])})

        assert await simple_store.count(filters=[QueryFilter(field="tags", operator="==", value=["x", "y"])]) == 1

    async def test_array_remove_drops_the_named_members(self, simple_store: SimpleStore) -> None:
        seeded = await _seed(simple_store, ("tagged",))
        await simple_store.mutate_fields(document_id=seeded["tagged"], field_updates={"tags": ArrayUnion(["x", "y"])})

        await simple_store.mutate_fields(document_id=seeded["tagged"], field_updates={"tags": ArrayRemove(["x"])})

        assert await simple_store.count(filters=[QueryFilter(field="tags", operator="array_contains", value="x")]) == 0
        assert await simple_store.count(filters=[QueryFilter(field="tags", operator="array_contains", value="y")]) == 1


class TestQuerying:
    @pytest.mark.parametrize(
        ("operator", "value", "expected"),
        [
            ("==", "b", ["b"]),
            ("!=", "b", ["a", "c"]),
            (">", "b", ["c"]),
            (">=", "b", ["b", "c"]),
            ("<", "b", ["a"]),
            ("<=", "b", ["a", "b"]),
            ("in", ["a", "c"], ["a", "c"]),
            ("not_in", ["a", "c"], ["b"]),
        ],
    )
    async def test_every_scalar_query_operator_selects_the_right_documents(
        self, simple_store: SimpleStore, operator: QueryOperator, value: Primitive, expected: list[str]
    ) -> None:
        await _seed(simple_store, ("a", "b", "c"))

        result = await simple_store.query(filters=[QueryFilter(field="name", operator=operator, value=value)])

        assert sorted(entity.name for entity in result.entities) == expected

    async def test_array_contains_selects_documents_holding_the_member(self, simple_store: SimpleStore) -> None:
        seeded = await _seed(simple_store, ("a", "b"))
        await simple_store.mutate_fields(document_id=seeded["b"], field_updates={"tags": ArrayUnion(["x"])})

        result = await simple_store.query(filters=[QueryFilter(field="tags", operator="array_contains", value="x")])

        assert [entity.name for entity in result.entities] == ["b"]

    async def test_sorting_ascending(self, simple_store: SimpleStore) -> None:
        await _seed(simple_store, ("b", "c", "a"))

        result = await simple_store.query(sort_by=SortBy(field="name", direction="ASCENDING"))

        assert [entity.name for entity in result.entities] == ["a", "b", "c"]

    async def test_sorting_descending(self, simple_store: SimpleStore) -> None:
        await _seed(simple_store, ("b", "c", "a"))

        result = await simple_store.query(sort_by=SortBy(field="name", direction="DESCENDING"))

        assert [entity.name for entity in result.entities] == ["c", "b", "a"]

    async def test_a_limit_shorter_than_the_result_reports_more(self, simple_store: SimpleStore) -> None:
        await _seed(simple_store, ("a", "b", "c"))

        result = await simple_store.query(sort_by=SortBy(field="name", direction="ASCENDING"), limit=2)

        assert [entity.name for entity in result.entities] == ["a", "b"]
        assert result.has_more is True

    async def test_a_limit_that_covers_everything_reports_no_more(self, simple_store: SimpleStore) -> None:
        await _seed(simple_store, ("a", "b", "c"))

        result = await simple_store.query(sort_by=SortBy(field="name", direction="ASCENDING"), limit=3)

        assert [entity.name for entity in result.entities] == ["a", "b", "c"]
        assert result.has_more is False

    async def test_a_cursor_resumes_after_the_previous_page(self, simple_store: SimpleStore) -> None:
        await _seed(simple_store, ("a", "b", "c"))
        sort_by = SortBy(field="name", direction="ASCENDING")
        first_page = await simple_store.query(sort_by=sort_by, limit=2)

        second_page = await simple_store.query(sort_by=sort_by, cursor={"name": first_page.entities[-1].name})

        assert [entity.name for entity in second_page.entities] == ["c"]
        assert second_page.has_more is False

    async def test_query_ids_returns_the_matching_document_ids(self, simple_store: SimpleStore) -> None:
        seeded = await _seed(simple_store, ("a", "b", "c"))

        document_ids = await simple_store.query_ids(filters=[QueryFilter(field="name", operator="==", value="b")])

        assert document_ids == [seeded["b"]]

    async def test_query_ids_honours_a_limit(self, simple_store: SimpleStore) -> None:
        await _seed(simple_store, ("a", "b", "c"))

        document_ids = await simple_store.query_ids(sort_by=SortBy(field="name", direction="ASCENDING"), limit=2)

        assert len(document_ids) == 2

    async def test_query_one_returns_the_single_match(self, simple_store: SimpleStore) -> None:
        await _seed(simple_store, ("a", "b", "c"))

        entity = await simple_store.query_one(filters=[QueryFilter(field="name", operator="==", value="b")])

        assert entity is not None
        assert entity.name == "b"

    async def test_query_one_returns_none_when_nothing_matches(self, simple_store: SimpleStore) -> None:
        await _seed(simple_store, ("a", "b", "c"))

        assert await simple_store.query_one(filters=[QueryFilter(field="name", operator="==", value="z")]) is None

    async def test_query_one_refuses_an_ambiguous_result(self, simple_store: SimpleStore) -> None:
        await _seed(simple_store, ("a", "b", "c"))

        with pytest.raises(InfrastructureError):
            await simple_store.query_one(filters=[QueryFilter(field="name", operator="!=", value="z")])

    async def test_count_without_filters_counts_the_whole_collection(self, simple_store: SimpleStore) -> None:
        await _seed(simple_store, ("a", "b", "c"))

        assert await simple_store.count() == 3

    async def test_count_ignores_documents_that_do_not_match(self, simple_store: SimpleStore) -> None:
        await _seed(simple_store, ("a", "b", "c"))

        assert await simple_store.count(filters=[QueryFilter(field="name", operator="<", value="c")]) == 2


class TestSubcollections:
    async def test_subentities_of_every_identity_shape_survive_a_round_trip(self, main_store: MainStore) -> None:
        entity = MainEntity(
            id=MainId(),
            string_subs=[StringSub(id=StringSubId())],
            int_subs=[IntSub(id=IntSubId(1)), IntSub(id=IntSubId(2))],
            composite_subs=[CompositeSub(id=CompositeSubId(org="acme", user="nash"))],
        )
        document_id = main_store.to_document_id(entity.id)

        await main_store.set(document_id=document_id, document_data=entity)
        read = await main_store.get(document_id=document_id)

        assert read == entity

    async def test_a_removed_subentity_is_pruned_on_the_next_write(self, main_store: MainStore) -> None:
        kept, dropped = IntSub(id=IntSubId(1)), IntSub(id=IntSubId(2))
        entity = MainEntity(id=MainId(), int_subs=[kept, dropped])
        document_id = main_store.to_document_id(entity.id)
        await main_store.set(document_id=document_id, document_data=entity)

        entity.int_subs = [kept]
        await main_store.set(document_id=document_id, document_data=entity)

        assert [sub.id for sub in (await main_store.get(document_id=document_id)).int_subs] == [kept.id]

    async def test_a_shallow_query_returns_counts_but_not_subentities(self, main_store: MainStore) -> None:
        entity = MainEntity(id=MainId(), int_subs=[IntSub(id=IntSubId(1)), IntSub(id=IntSubId(2))])
        await main_store.set(document_id=main_store.to_document_id(entity.id), document_data=entity)

        result = await main_store.query(mode="shallow")

        assert result.entities[0].int_subs == []
        assert result.subcollection_counts == [{"string_subs": 0, "int_subs": 2, "composite_subs": 0}]

    async def test_a_deep_query_returns_the_subentities(self, main_store: MainStore) -> None:
        entity = MainEntity(id=MainId(), int_subs=[IntSub(id=IntSubId(1)), IntSub(id=IntSubId(2))])
        await main_store.set(document_id=main_store.to_document_id(entity.id), document_data=entity)

        result = await main_store.query(mode="deep")

        assert sorted(sub.id for sub in result.entities[0].int_subs) == [IntSubId(1), IntSubId(2)]

    async def test_a_deleted_document_does_not_resurrect_its_subentities(self, main_store: MainStore) -> None:
        entity = MainEntity(id=MainId(), int_subs=[IntSub(id=IntSubId(1))])
        document_id = main_store.to_document_id(entity.id)
        await main_store.set(document_id=document_id, document_data=entity)

        await main_store.delete(document_id=document_id)
        entity.int_subs = []
        await main_store.set(document_id=document_id, document_data=entity)

        assert (await main_store.get(document_id=document_id)).int_subs == []
