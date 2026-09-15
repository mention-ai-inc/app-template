import inspect

import pytest

from library.application.errors import ApplicationError, ApplicationErrorType
from library.application.ports.documents import DocumentID, Increment, QueryFilter
from library.application.ports.provider import ICloudProvider
from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType
from tests.application.ports.conformance.stores import SimpleStore
from tests.infrastructure.persistence.mocks import MainId, SimpleEntity


async def _store_document(store: SimpleStore, *, name: str) -> DocumentID:
    entity = SimpleEntity(id=MainId(), name=name)
    document_id = store.to_document_id(entity.id)
    await store.set(document_id=document_id, document_data=entity)
    return document_id


class TestUnitOfWorkLifecycle:
    def test_asking_for_a_transaction_outside_a_block_raises(self, provider: ICloudProvider) -> None:
        with pytest.raises(InfrastructureError) as exc_info:
            provider.current_transaction()

        assert exc_info.value.error_type == InfrastructureErrorType.ENVIRONMENT_ERROR

    async def test_the_transaction_is_gone_once_the_block_closes(self, provider: ICloudProvider) -> None:
        async with provider.unit_of_work():
            provider.current_transaction()

        with pytest.raises(InfrastructureError):
            provider.current_transaction()


class TestAtomicity:
    async def test_writes_are_invisible_until_the_block_closes(
        self, provider: ICloudProvider, simple_store: SimpleStore
    ) -> None:
        entity = SimpleEntity(id=MainId(), name="pending")
        document_id = simple_store.to_document_id(entity.id)

        async with provider.unit_of_work():
            await simple_store.set(document_id=document_id, document_data=entity, uow=provider.current_transaction())
            assert await simple_store.exists(document_id=document_id) is False

        assert await simple_store.exists(document_id=document_id) is True

    async def test_every_write_in_a_block_lands_together(
        self, provider: ICloudProvider, simple_store: SimpleStore
    ) -> None:
        first = SimpleEntity(id=MainId(), name="first")
        second = SimpleEntity(id=MainId(), name="second")

        async with provider.unit_of_work():
            uow = provider.current_transaction()
            await simple_store.set(document_id=simple_store.to_document_id(first.id), document_data=first, uow=uow)
            await simple_store.set(document_id=simple_store.to_document_id(second.id), document_data=second, uow=uow)

        assert await simple_store.count() == 2

    async def test_a_failed_block_writes_nothing(self, provider: ICloudProvider, simple_store: SimpleStore) -> None:
        entity = SimpleEntity(id=MainId(), name="doomed")

        with pytest.raises(RuntimeError):
            async with provider.unit_of_work():
                await simple_store.set(
                    document_id=simple_store.to_document_id(entity.id),
                    document_data=entity,
                    uow=provider.current_transaction(),
                )
                raise RuntimeError("use case failed")

        assert await simple_store.count() == 0

    async def test_a_failed_block_discards_a_delete(self, provider: ICloudProvider, simple_store: SimpleStore) -> None:
        document_id = await _store_document(simple_store, name="survivor")

        with pytest.raises(RuntimeError):
            async with provider.unit_of_work():
                await simple_store.delete(document_id=document_id, uow=provider.current_transaction())
                raise RuntimeError("use case failed")

        assert await simple_store.exists(document_id=document_id) is True

    async def test_reading_after_writing_inside_a_block_is_refused(
        self, provider: ICloudProvider, simple_store: SimpleStore
    ) -> None:
        entity = SimpleEntity(id=MainId(), name="written")

        with pytest.raises(InfrastructureError):
            async with provider.unit_of_work():
                uow = provider.current_transaction()
                await simple_store.set(
                    document_id=simple_store.to_document_id(entity.id), document_data=entity, uow=uow
                )
                await simple_store.get(document_id=simple_store.to_document_id(entity.id), uow=uow)


class TestOptimisticConcurrency:
    async def test_a_document_changed_since_it_was_read_aborts_the_commit(
        self, provider: ICloudProvider, simple_store: SimpleStore
    ) -> None:
        document_id = await _store_document(simple_store, name="original")

        with pytest.raises(ApplicationError) as exc_info:
            async with provider.unit_of_work():
                uow = provider.current_transaction()
                read = await simple_store.get(document_id=document_id, uow=uow)
                await simple_store.field_set(document_id=document_id, field="name", value="someone else")
                read.name = "mine"
                await simple_store.set(document_id=document_id, document_data=read, uow=uow)

        assert exc_info.value.error_type == ApplicationErrorType.TRANSACTION_CONFLICT

    async def test_an_uncontended_read_then_write_commits(
        self, provider: ICloudProvider, simple_store: SimpleStore
    ) -> None:
        document_id = await _store_document(simple_store, name="original")

        async with provider.unit_of_work():
            uow = provider.current_transaction()
            read = await simple_store.get(document_id=document_id, uow=uow)
            read.name = "updated"
            await simple_store.set(document_id=document_id, document_data=read, uow=uow)

        assert (await simple_store.get(document_id=document_id)).name == "updated"


class TestUpdateFields:
    def test_update_fields_demands_a_unit_of_work(self, simple_store: SimpleStore) -> None:
        parameter = inspect.signature(simple_store.update_fields).parameters["uow"]

        assert parameter.default is inspect.Parameter.empty

    async def test_update_fields_lands_when_the_block_commits(
        self, provider: ICloudProvider, simple_store: SimpleStore
    ) -> None:
        document_id = await _store_document(simple_store, name="before")

        async with provider.unit_of_work():
            await simple_store.update_fields(
                document_id=document_id, field_updates={"name": "after"}, uow=provider.current_transaction()
            )

        assert (await simple_store.get(document_id=document_id)).name == "after"

    async def test_update_fields_is_discarded_when_the_block_fails(
        self, provider: ICloudProvider, simple_store: SimpleStore
    ) -> None:
        document_id = await _store_document(simple_store, name="before")

        with pytest.raises(RuntimeError):
            async with provider.unit_of_work():
                await simple_store.update_fields(
                    document_id=document_id, field_updates={"name": "after"}, uow=provider.current_transaction()
                )
                raise RuntimeError("use case failed")

        assert (await simple_store.get(document_id=document_id)).name == "before"


class TestWritesOutsideTheTransaction:
    async def test_field_set_lands_even_when_the_block_fails(
        self, provider: ICloudProvider, simple_store: SimpleStore
    ) -> None:
        document_id = await _store_document(simple_store, name="before")

        with pytest.raises(RuntimeError):
            async with provider.unit_of_work():
                await simple_store.field_set(document_id=document_id, field="name", value="after")
                raise RuntimeError("use case failed")

        assert (await simple_store.get(document_id=document_id)).name == "after"

    async def test_mutate_fields_lands_even_when_the_block_fails(
        self, provider: ICloudProvider, simple_store: SimpleStore
    ) -> None:
        document_id = await _store_document(simple_store, name="counted")

        with pytest.raises(RuntimeError):
            async with provider.unit_of_work():
                await simple_store.mutate_fields(document_id=document_id, field_updates={"counter": Increment(5)})
                raise RuntimeError("use case failed")

        assert await simple_store.count(filters=[QueryFilter(field="counter", operator="==", value=5)]) == 1

    async def test_set_merge_lands_even_when_the_block_fails(
        self, provider: ICloudProvider, simple_store: SimpleStore
    ) -> None:
        document_id = await _store_document(simple_store, name="before")

        with pytest.raises(RuntimeError):
            async with provider.unit_of_work():
                await simple_store.set_merge(document_id=document_id, document_data={"name": "after"})
                raise RuntimeError("use case failed")

        assert (await simple_store.get(document_id=document_id)).name == "after"
