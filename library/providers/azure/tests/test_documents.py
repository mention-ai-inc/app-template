from datetime import UTC, datetime

import pytest
from tests.infrastructure.persistence.mocks import CompositeSubId, IntSubId, MainEntity, MockPartitionKey

from library.application.ports.documents import ArrayRemove, ArrayUnion, DocumentID, Increment, QueryFilter
from library.domain.value_objects.common import Service
from library.infrastructure.errors import InfrastructureError
from library_provider_azure.documents import (
    DOCUMENT_ID_FIELD,
    DOCUMENT_TYPE_FIELD,
    ENTITY_ID_FIELD,
    PARTITION_KEY_FIELD,
    CosmosDocumentStore,
    to_cosmos_id,
    to_cosmos_item,
    to_cosmos_value,
    to_partition_value,
    to_patch_operations,
    to_record,
    to_sql_condition,
    to_subcollection_type,
)
from library_provider_azure.provider import AzureProvider

ORGANIZATION_ID = "org_1"
DOCUMENT_ID = DocumentID("main_1")


def store(*, collection: str = "simple") -> CosmosDocumentStore[MainEntity, MockPartitionKey]:
    return CosmosDocumentStore(
        collection=collection, model=MainEntity, partition_key_type=MockPartitionKey, service=Service.NOTES
    )


class TestTheContainer:
    def test_every_document_type_of_a_service_shares_the_service_container(self) -> None:
        assert store(collection="simple").container_name == store(collection="main").container_name == "notes"

    def test_a_store_without_a_service_has_no_container_to_reach(self) -> None:
        with pytest.raises(InfrastructureError, match="one container per service"):
            CosmosDocumentStore(
                collection="simple", model=MainEntity, partition_key_type=MockPartitionKey, service=""
            ).container_name


class TestTheItem:
    def test_the_collection_id_becomes_the_document_type_discriminator(self) -> None:
        item = to_cosmos_item(
            document_type="notes_simple", document_id=DOCUMENT_ID, partition_value=ORGANIZATION_ID, record={}
        )

        assert item[DOCUMENT_TYPE_FIELD] == "notes_simple"

    def test_the_item_id_carries_the_document_type_so_two_collections_cannot_collide(self) -> None:
        simple = to_cosmos_id(document_type="notes_simple", document_id=DOCUMENT_ID)
        main = to_cosmos_id(document_type="notes_main", document_id=DOCUMENT_ID)

        assert simple == "notes_simple:main_1"
        assert simple != main

    def test_an_item_id_that_cosmos_cannot_hold_is_refused(self) -> None:
        with pytest.raises(InfrastructureError, match="cannot contain"):
            to_cosmos_id(document_type="notes_simple", document_id=DocumentID("a/b"))

    def test_the_entity_identity_is_kept_beside_the_item_id_in_its_own_json_shape(self) -> None:
        item = to_cosmos_item(
            document_type="notes_simple", document_id=DocumentID("7"), partition_value=ORGANIZATION_ID, record={"id": 7}
        )

        assert item[ENTITY_ID_FIELD] == 7
        assert item[DOCUMENT_ID_FIELD] == "7"

    def test_the_partition_value_is_a_field_rather_than_a_path(self) -> None:
        item = to_cosmos_item(
            document_type="notes_simple", document_id=DOCUMENT_ID, partition_value=ORGANIZATION_ID, record={}
        )

        assert item[PARTITION_KEY_FIELD] == ORGANIZATION_ID

    def test_an_item_round_trips_back_to_the_record_it_was_built_from(self) -> None:
        record = {"id": "main_1", "name": "hammer"}

        item = to_cosmos_item(
            document_type="notes_simple",
            document_id=DOCUMENT_ID,
            partition_value=ORGANIZATION_ID,
            record=record,
        )

        assert to_record({**item, "_etag": "etag-1", "_ts": 1}) == record

    def test_a_subcollection_is_a_document_type_of_its_own_inside_the_same_container(self) -> None:
        subcollection_type = to_subcollection_type(
            collection_id="notes_main", document_id=DOCUMENT_ID, subentity_name="int_subs"
        )

        assert subcollection_type == "notes_main|main_1|int_subs"
        assert "/" not in to_cosmos_id(document_type=subcollection_type, document_id=DocumentID("1"))


class TestPartitioning:
    def test_a_connected_partition_is_the_partition_value(self) -> None:
        partition_key = MockPartitionKey()

        with store().connect_to_partition(partition_key) as scoped:
            assert scoped.active_partition_key == partition_key

    def test_an_unpartitioned_collection_takes_the_organization_off_the_document(self) -> None:
        value = to_partition_value(collection_id="notes_commands", record={"organization_id": ORGANIZATION_ID})

        assert value == ORGANIZATION_ID

    def test_a_document_that_names_no_organization_shares_the_partition_of_its_collection(self) -> None:
        assert to_partition_value(collection_id="notes_simple", record={}) == "notes_simple"


class TestIdentities:
    def test_an_integer_identity_survives_as_a_decimal_document_id(self) -> None:
        assert store().to_document_id(IntSubId(7)) == "7"

    def test_a_composite_identity_becomes_an_id_a_cosmos_item_can_hold(self) -> None:
        document_id = store().to_document_id(CompositeSubId(org="acme", user="nash"))

        assert all(character not in document_id for character in ("/", "\\", "?", "#"))
        assert CompositeSubId.from_id(id=document_id) == CompositeSubId(org="acme", user="nash")


class TestFieldUpdates:
    def test_an_increment_is_resolved_against_the_value_that_was_read(self) -> None:
        operations = to_patch_operations({"counter": Increment(3)}, item={"counter": 4})

        assert operations == [{"op": "set", "path": "/counter", "value": 7}]

    def test_an_increment_of_an_absent_field_starts_from_zero(self) -> None:
        assert to_patch_operations({"counter": Increment(3)}, item={}) == [
            {"op": "set", "path": "/counter", "value": 3}
        ]

    def test_an_array_union_does_not_duplicate_a_member_that_is_already_there(self) -> None:
        operations = to_patch_operations({"tags": ArrayUnion(["x", "y"])}, item={"tags": ["x"]})

        assert operations == [{"op": "set", "path": "/tags", "value": ["x", "y"]}]

    def test_an_array_remove_drops_the_named_members(self) -> None:
        operations = to_patch_operations({"tags": ArrayRemove(["x"])}, item={"tags": ["x", "y"]})

        assert operations == [{"op": "set", "path": "/tags", "value": ["y"]}]


class TestQueryTranslation:
    @pytest.mark.parametrize(
        ("operator", "expected"),
        [
            ("==", "c.name = @p"),
            ("!=", "c.name != @p"),
            (">", "c.name > @p"),
            (">=", "c.name >= @p"),
            ("<", "c.name < @p"),
            ("<=", "c.name <= @p"),
            ("in", "ARRAY_CONTAINS(@p, c.name)"),
            ("not_in", "NOT ARRAY_CONTAINS(@p, c.name)"),
            ("array_contains", "ARRAY_CONTAINS(c.name, @p)"),
        ],
    )
    def test_every_query_operator_has_a_cosmos_sql_form(self, operator: str, expected: str) -> None:
        assert to_sql_condition(field="name", operator=operator, name="@p") == expected

    def test_an_operator_cosmos_cannot_express_is_refused(self) -> None:
        with pytest.raises(InfrastructureError, match="no SQL comparison"):
            to_sql_condition(field="name", operator="~=", name="@p")

    def test_a_datetime_filter_becomes_an_iso_string_cosmos_can_compare(self) -> None:
        query_filter = QueryFilter(field="created_at", operator=">", value=datetime(2026, 1, 1, tzinfo=UTC))

        assert to_cosmos_value(query_filter.value) == "2026-01-01T00:00:00+00:00"


def test_the_provider_hands_back_a_cosmos_document_store() -> None:
    assert isinstance(
        AzureProvider().document_store(
            collection="simple", model=MainEntity, partition_key_type=MockPartitionKey, service=Service.NOTES
        ),
        CosmosDocumentStore,
    )
