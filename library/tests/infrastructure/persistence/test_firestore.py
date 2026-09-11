from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

from library.application.errors import ApplicationError, ApplicationErrorType
from library.domain.value_objects.common import Service
from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType
from library.infrastructure.persistence.firestore import DocumentID, Firestore, QueryFilter
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
    make_doc_snapshot,
    patch_firestore_client,
)


async def _async_iter[T](items: list[T]) -> AsyncIterator[T]:
    for item in items:
        yield item


def _existing_snapshot(*, doc_id: str, name: str) -> MagicMock:
    snapshot = make_doc_snapshot(data={"id": doc_id, "name": name}, doc_id=doc_id)
    snapshot.exists = True
    return snapshot


def _missing_snapshot(*, doc_id: str) -> MagicMock:
    snapshot = make_doc_snapshot(data={}, doc_id=doc_id)
    snapshot.exists = False
    return snapshot


def _make_main_firestore() -> Firestore[MainEntity, MockPartitionKey]:
    return Firestore[MainEntity, MockPartitionKey](
        collection="main",
        model=MainEntity,
        partition_key_type=MockPartitionKey,
        service=Service.NOTES,
        feature_environment="",
    )


def _make_simple_firestore() -> Firestore[SimpleEntity, MockPartitionKey]:
    return Firestore[SimpleEntity, MockPartitionKey](
        collection="simple",
        model=SimpleEntity,
        partition_key_type=MockPartitionKey,
        service=Service.NOTES,
        feature_environment="",
    )


class TestClientPool:
    def test_get_client_round_robins_across_pool(self, mocker: MockerFixture) -> None:
        mocker.patch.object(Firestore, "DEFAULT_CLIENT_POOL_SIZE", 3)
        clients = [MagicMock(name=f"client_{i}") for i in range(3)]
        mocker.patch("library.infrastructure.persistence.firestore.firestore.AsyncClient", side_effect=clients)
        mocker.patch.object(Firestore, "_client_pool", None)
        mocker.patch.object(Firestore, "_client_pool_cursor", 0)

        returned = [Firestore.get_client() for _ in range(7)]

        assert returned == [clients[i % 3] for i in range(7)]

    def test_pool_built_once_at_configured_size(self, mocker: MockerFixture) -> None:
        mocker.patch.object(Firestore, "DEFAULT_CLIENT_POOL_SIZE", 2)
        async_client = mocker.patch(
            "library.infrastructure.persistence.firestore.firestore.AsyncClient",
            side_effect=[MagicMock(), MagicMock()],
        )
        mocker.patch.object(Firestore, "_client_pool", None)
        mocker.patch.object(Firestore, "_client_pool_cursor", 0)

        for _ in range(5):
            Firestore.get_client()

        assert async_client.call_count == 2


class TestQueryFilter:
    def test_in_operator_rejects_more_than_30_values(self) -> None:
        with pytest.raises(InfrastructureError) as exc_info:
            QueryFilter(field="id", operator="in", value=[str(i) for i in range(31)])

        assert exc_info.value.error_type == InfrastructureErrorType.VALIDATION_ERROR

    def test_in_operator_allows_exactly_30_values(self) -> None:
        QueryFilter(field="id", operator="in", value=[str(i) for i in range(30)])

    def test_in_operator_allows_few_values(self) -> None:
        QueryFilter(field="id", operator="in", value=["a", "b", "c"])

    def test_other_operators_have_no_size_limit(self) -> None:
        QueryFilter(field="ids", operator="==", value=[str(i) for i in range(50)])


class TestConnectToPartition:
    def test_modifies_collection_id_inside_context(self) -> None:
        firestore = _make_simple_firestore()
        original_id = firestore.collection_id
        partition_key = MockPartitionKey()

        with firestore.connect_to_partition(partition_key) as f:
            assert f.collection_id != original_id
            assert str(partition_key) in f.collection_id

    def test_does_not_mutate_the_shared_store(self) -> None:
        firestore = _make_simple_firestore()
        original_id = firestore.collection_id

        with firestore.connect_to_partition(MockPartitionKey()):
            assert firestore.collection_id == original_id

        assert firestore.collection_id == original_id

    def test_yields_a_scoped_copy_not_self(self) -> None:
        firestore = _make_simple_firestore()

        with firestore.connect_to_partition(MockPartitionKey()) as f:
            assert f is not firestore

    def test_concurrent_partition_contexts_are_isolated(self) -> None:
        firestore = _make_simple_firestore()
        key_a = MockPartitionKey()
        key_b = MockPartitionKey()

        with firestore.connect_to_partition(key_a) as store_a:
            with firestore.connect_to_partition(key_b) as store_b:
                assert str(key_b) in store_b.collection_id
            assert str(key_a) in store_a.collection_id
            assert str(key_b) not in store_a.collection_id


class TestClientForUow:
    async def test_transactional_read_uses_transaction_client_not_pool(self, mocker: MockerFixture) -> None:
        pool_client = patch_firestore_client(mocker)
        firestore = _make_simple_firestore()

        uow = MagicMock()
        txn_client = uow._client
        txn_client.collection.return_value.document.return_value.get = AsyncMock(
            return_value=_existing_snapshot(doc_id="main_x", name="n")
        )

        with firestore.connect_to_partition(MockPartitionKey()) as store:
            await store.get(document_id=DocumentID("main_x"), uow=uow)

        txn_client.collection.assert_called()
        pool_client.collection.assert_not_called()

    def test_non_transactional_op_uses_pool_client(self, mocker: MockerFixture) -> None:
        pool_client = patch_firestore_client(mocker)
        firestore = _make_simple_firestore()

        assert firestore.client_for_uow(None) is pool_client


class TestSetSubentityIdEncoding:
    async def test_encodes_string_int_and_model_value_object_ids(self, mocker: MockerFixture) -> None:
        patch_firestore_client(mocker)
        firestore = _make_main_firestore()
        mock_uow = MagicMock()
        composite_sub = CompositeSub(id=CompositeSubId(org="acme", user="alice"))
        main_entity = MainEntity(
            id=MainId(),
            string_subs=[StringSub(id=StringSubId("ssub_abc123"))],
            int_subs=[IntSub(id=IntSubId(42))],
            composite_subs=[composite_sub],
        )

        await firestore.set(
            document_id=DocumentID(main_entity.id),
            document_data=main_entity,
            uow=mock_uow,
        )

        metadata = mock_uow.set.call_args_list[-1].args[1]["_subcollection_metadata"]

        assert metadata["string_subs"] == ["ssub_abc123"]
        assert metadata["int_subs"] == ["42"]
        assert metadata["composite_subs"] == [composite_sub.id.to_id()]

    async def test_model_value_object_id_round_trips_via_to_id(self, mocker: MockerFixture) -> None:
        patch_firestore_client(mocker)
        firestore = _make_main_firestore()
        mock_uow = MagicMock()
        composite_id = CompositeSubId(org="o1", user="u1")
        main_entity = MainEntity(id=MainId(), composite_subs=[CompositeSub(id=composite_id)])

        await firestore.set(
            document_id=DocumentID(main_entity.id),
            document_data=main_entity,
            uow=mock_uow,
        )

        encoded = mock_uow.set.call_args_list[-1].args[1]["_subcollection_metadata"]["composite_subs"][0]
        assert CompositeSubId.from_id(id=encoded) == composite_id


class TestSetPrunesOrphanedSubdocuments:
    async def test_deletes_subdocuments_dropped_from_the_metadata(self, mocker: MockerFixture) -> None:
        mock_client = patch_firestore_client(mocker)
        _commit_subcollection_metadata(mock_client, {"string_subs": ["ssub_keep", "ssub_drop"]})
        firestore = _make_main_firestore()
        mock_uow = MagicMock()
        main_entity = MainEntity(id=MainId(), string_subs=[StringSub(id=StringSubId("ssub_keep"))])

        await firestore.set(document_id=DocumentID(main_entity.id), document_data=main_entity, uow=mock_uow)

        subcollection = mock_uow._client.collection.return_value.document.return_value.collection.return_value
        assert mock_uow.delete.call_count == 1
        assert subcollection.document.call_args_list[-1].args == ("ssub_drop",)

    async def test_keeps_subdocuments_that_are_still_present(self, mocker: MockerFixture) -> None:
        mock_client = patch_firestore_client(mocker)
        _commit_subcollection_metadata(mock_client, {"string_subs": ["ssub_keep"]})
        firestore = _make_main_firestore()
        mock_uow = MagicMock()
        main_entity = MainEntity(id=MainId(), string_subs=[StringSub(id=StringSubId("ssub_keep"))])

        await firestore.set(document_id=DocumentID(main_entity.id), document_data=main_entity, uow=mock_uow)

        assert mock_uow.delete.call_count == 0

    async def test_prunes_nothing_when_the_document_is_new(self, mocker: MockerFixture) -> None:
        patch_firestore_client(mocker)
        firestore = _make_main_firestore()
        mock_uow = MagicMock()
        main_entity = MainEntity(id=MainId(), string_subs=[StringSub(id=StringSubId("ssub_new"))])

        await firestore.set(document_id=DocumentID(main_entity.id), document_data=main_entity, uow=mock_uow)

        assert mock_uow.delete.call_count == 0

    async def test_reads_the_previous_metadata_outside_the_transaction(self, mocker: MockerFixture) -> None:
        mock_client = patch_firestore_client(mocker)
        _commit_subcollection_metadata(mock_client, {"string_subs": []})
        firestore = _make_main_firestore()
        mock_uow = MagicMock()
        main_entity = MainEntity(id=MainId(), string_subs=[])

        await firestore.set(document_id=DocumentID(main_entity.id), document_data=main_entity, uow=mock_uow)

        document_get = mock_client.collection.return_value.document.return_value.get
        assert document_get.await_args.kwargs == {"field_paths": ["_subcollection_metadata"]}


def _commit_subcollection_metadata(mock_client: MagicMock, metadata: dict[str, list[str]]) -> None:
    snapshot = make_doc_snapshot(data={"_subcollection_metadata": metadata}, doc_id="existing")
    snapshot.exists = True
    mock_client.collection.return_value.document.return_value.get = AsyncMock(return_value=snapshot)


class TestNonTransactionalWrites:
    async def test_set_without_uow_writes_directly(self, mocker: MockerFixture) -> None:
        mock_client = patch_firestore_client(mocker)
        document = mock_client.collection.return_value.document.return_value
        document.set = AsyncMock()
        firestore = _make_simple_firestore()
        entity = SimpleEntity(id=MainId(), name="n0")

        await firestore.set(document_id=DocumentID(entity.id), document_data=entity)

        document.set.assert_awaited_once()
        written = document.set.call_args.args[0]
        assert written["name"] == "n0"

    async def test_set_with_uow_buffers_into_transaction(self, mocker: MockerFixture) -> None:
        patch_firestore_client(mocker)
        firestore = _make_simple_firestore()
        mock_uow = MagicMock()
        entity = SimpleEntity(id=MainId(), name="n0")

        await firestore.set(document_id=DocumentID(entity.id), document_data=entity, uow=mock_uow)

        mock_uow.set.assert_called_once()

    async def test_delete_without_uow_deletes_directly(self, mocker: MockerFixture) -> None:
        mock_client = patch_firestore_client(mocker)
        document = mock_client.collection.return_value.document.return_value
        document.delete = AsyncMock()
        firestore = _make_simple_firestore()

        await firestore.delete(document_id=DocumentID("main_0"))

        document.delete.assert_awaited_once()


class TestQueryPagination:
    async def test_returns_limit_entities_and_has_more_when_underlying_yields_more(self, mocker: MockerFixture) -> None:
        mock_client = patch_firestore_client(mocker)
        firestore = _make_simple_firestore()
        docs = [make_doc_snapshot(data={"id": f"main_{i}", "name": f"n{i}"}, doc_id=f"main_{i}") for i in range(3)]
        mock_client.collection.return_value.get = AsyncMock(return_value=docs)

        result = await firestore.query(limit=2)

        assert len(result.entities) == 2
        assert result.has_more is True
        assert result.entities[0].id == "main_0"
        assert result.entities[1].id == "main_1"

    async def test_has_more_false_when_underlying_yields_exactly_limit(self, mocker: MockerFixture) -> None:
        mock_client = patch_firestore_client(mocker)
        firestore = _make_simple_firestore()
        docs = [make_doc_snapshot(data={"id": f"main_{i}", "name": f"n{i}"}, doc_id=f"main_{i}") for i in range(2)]
        mock_client.collection.return_value.get = AsyncMock(return_value=docs)

        result = await firestore.query(limit=2)

        assert len(result.entities) == 2
        assert result.has_more is False

    async def test_has_more_false_when_underlying_yields_below_limit(self, mocker: MockerFixture) -> None:
        mock_client = patch_firestore_client(mocker)
        firestore = _make_simple_firestore()
        docs = [make_doc_snapshot(data={"id": "main_0", "name": "n0"}, doc_id="main_0")]
        mock_client.collection.return_value.get = AsyncMock(return_value=docs)

        result = await firestore.query(limit=5)

        assert len(result.entities) == 1
        assert result.has_more is False

    async def test_has_more_false_when_no_limit_specified(self, mocker: MockerFixture) -> None:
        mock_client = patch_firestore_client(mocker)
        firestore = _make_simple_firestore()
        docs = [make_doc_snapshot(data={"id": f"main_{i}", "name": f"n{i}"}, doc_id=f"main_{i}") for i in range(5)]
        mock_client.collection.return_value.get = AsyncMock(return_value=docs)

        result = await firestore.query()

        assert len(result.entities) == 5
        assert result.has_more is False

    async def test_query_passes_limit_plus_one_to_underlying(self, mocker: MockerFixture) -> None:
        mock_client = patch_firestore_client(mocker)
        firestore = _make_simple_firestore()
        chainable = mock_client.collection.return_value
        chainable.get = AsyncMock(return_value=[])

        await firestore.query(limit=10)

        chainable.limit.assert_called_with(11)


class TestGetMany:
    async def test_returns_all_entities_when_every_document_exists(self, mocker: MockerFixture) -> None:
        mock_client = patch_firestore_client(mocker)
        firestore = _make_simple_firestore()
        snapshots = [_existing_snapshot(doc_id="main_0", name="n0"), _existing_snapshot(doc_id="main_1", name="n1")]
        mock_client.get_all = MagicMock(return_value=_async_iter(snapshots))

        entities = await firestore.get_many(document_ids=[DocumentID("main_0"), DocumentID("main_1")])

        assert [entity.id for entity in entities] == ["main_0", "main_1"]

    async def test_raises_when_a_document_is_missing_by_default(self, mocker: MockerFixture) -> None:
        mock_client = patch_firestore_client(mocker)
        firestore = _make_simple_firestore()
        snapshots = [_existing_snapshot(doc_id="main_0", name="n0"), _missing_snapshot(doc_id="main_1")]
        mock_client.get_all = MagicMock(return_value=_async_iter(snapshots))

        with pytest.raises(ApplicationError) as exc_info:
            await firestore.get_many(document_ids=[DocumentID("main_0"), DocumentID("main_1")])

        assert exc_info.value.error_type == ApplicationErrorType.RESOURCE_NOT_FOUND

    async def test_skips_missing_documents_when_ignore_missing(self, mocker: MockerFixture) -> None:
        mock_client = patch_firestore_client(mocker)
        firestore = _make_simple_firestore()
        snapshots = [_existing_snapshot(doc_id="main_0", name="n0"), _missing_snapshot(doc_id="main_1")]
        mock_client.get_all = MagicMock(return_value=_async_iter(snapshots))

        entities = await firestore.get_many(
            document_ids=[DocumentID("main_0"), DocumentID("main_1")], ignore_missing=True
        )

        assert [entity.id for entity in entities] == ["main_0"]
