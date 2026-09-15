import pytest
from azure.cosmos.exceptions import CosmosHttpResponseError
from pytest_mock import MockerFixture

from library.application.errors import ApplicationError, ApplicationErrorType
from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType
from library_provider_azure.transactions import MAX_BATCH_OPERATIONS, BufferedWrite, CosmosTransaction
from library_provider_azure.unit_of_work import azure_unit_of_work, commit, get_current_azure_transaction

CONTAINER = "notes"
PARTITION = "org_1"


def buffered(
    *, cosmos_id: str, partition_value: str = PARTITION, operation: str = "upsert", etag: str | None = None
) -> BufferedWrite:
    return BufferedWrite(
        container_name=CONTAINER,
        cosmos_id=cosmos_id,
        partition_value=partition_value,
        operation=operation,  # pyright: ignore[reportArgumentType]
        item={"id": cosmos_id},
        patch_operations=None,
        etag=etag,
    )


@pytest.fixture
def batches(mocker: MockerFixture) -> list[tuple[list[tuple[str, tuple[object, ...], dict[str, object]]], str]]:
    recorded: list[tuple[list[tuple[str, tuple[object, ...], dict[str, object]]], str]] = []

    async def execute_item_batch(
        *, batch_operations: list[tuple[str, tuple[object, ...], dict[str, object]]], partition_key: str
    ) -> None:
        recorded.append((batch_operations, partition_key))

    container = mocker.MagicMock()
    container.execute_item_batch = execute_item_batch
    mocker.patch("library_provider_azure.unit_of_work.AzureClients.container", return_value=container)
    return recorded


class TestLifecycle:
    async def test_the_transaction_only_exists_inside_the_block(self, batches: object) -> None:  # noqa: ARG002
        with pytest.raises(InfrastructureError) as before:
            get_current_azure_transaction()

        async with azure_unit_of_work():
            assert isinstance(get_current_azure_transaction(), CosmosTransaction)

        assert before.value.error_type == InfrastructureErrorType.ENVIRONMENT_ERROR

    async def test_a_block_that_buffered_nothing_sends_no_batch(self, batches: list[tuple[list[object], str]]) -> None:
        async with azure_unit_of_work():
            get_current_azure_transaction()

        assert batches == []


class TestTheBatch:
    async def test_every_buffered_write_becomes_one_operation_in_one_partition(
        self, batches: list[tuple[list[tuple[str, tuple[object, ...], dict[str, object]]], str]]
    ) -> None:
        transaction = CosmosTransaction()
        transaction.writes = [buffered(cosmos_id="a"), buffered(cosmos_id="b", operation="delete")]

        await commit(transaction)

        operations, partition_key = batches[0]
        assert [operation for operation, _, _ in operations] == ["upsert", "delete"]
        assert partition_key == PARTITION

    async def test_a_document_read_inside_the_block_is_written_back_with_its_etag(
        self, batches: list[tuple[list[tuple[str, tuple[object, ...], dict[str, object]]], str]]
    ) -> None:
        transaction = CosmosTransaction()
        transaction.writes = [buffered(cosmos_id="a", etag="etag-1")]

        await commit(transaction)

        operations, _ = batches[0]
        assert operations[0][2] == {"if_match_etag": "etag-1"}

    async def test_writing_the_same_document_twice_collapses_to_its_last_state(
        self, batches: list[tuple[list[tuple[str, tuple[object, ...], dict[str, object]]], str]]
    ) -> None:
        transaction = CosmosTransaction()
        transaction.writes = [buffered(cosmos_id="a"), buffered(cosmos_id="a", operation="delete")]

        await commit(transaction)

        operations, _ = batches[0]
        assert [operation for operation, _, _ in operations] == ["delete"]


class TestTheSinglePartitionConstraint:
    async def test_a_block_that_spans_two_logical_partitions_refuses_to_commit(
        self, batches: list[tuple[list[object], str]]
    ) -> None:
        transaction = CosmosTransaction()
        transaction.writes = [buffered(cosmos_id="a"), buffered(cosmos_id="b", partition_value="org_2")]

        with pytest.raises(InfrastructureError) as exc_info:
            await commit(transaction)

        assert "one logical partition" in exc_info.value.message
        assert batches == []

    async def test_a_block_larger_than_a_batch_refuses_to_commit(self, batches: list[tuple[list[object], str]]) -> None:
        transaction = CosmosTransaction()
        transaction.writes = [buffered(cosmos_id=f"a{index}") for index in range(MAX_BATCH_OPERATIONS + 1)]

        with pytest.raises(InfrastructureError) as exc_info:
            await commit(transaction)

        assert str(MAX_BATCH_OPERATIONS) in exc_info.value.message
        assert batches == []


class TestContention:
    @pytest.mark.parametrize("status_code", [409, 412, 449, 429])
    async def test_a_contended_batch_becomes_a_transaction_conflict(
        self, mocker: MockerFixture, status_code: int
    ) -> None:
        self.__reject_with(mocker, status_code=status_code)
        transaction = CosmosTransaction()
        transaction.writes = [buffered(cosmos_id="a")]

        with pytest.raises(ApplicationError) as exc_info:
            await commit(transaction)

        assert exc_info.value.error_type == ApplicationErrorType.TRANSACTION_CONFLICT

    async def test_any_other_rejection_stays_an_infrastructure_error(self, mocker: MockerFixture) -> None:
        self.__reject_with(mocker, status_code=400)
        transaction = CosmosTransaction()
        transaction.writes = [buffered(cosmos_id="a")]

        with pytest.raises(InfrastructureError) as exc_info:
            await commit(transaction)

        assert exc_info.value.error_type == InfrastructureErrorType.CLOUD_ERROR

    def __reject_with(self, mocker: MockerFixture, *, status_code: int) -> None:
        error = CosmosHttpResponseError(message="rejected")
        error.status_code = status_code

        async def execute_item_batch(**_: object) -> None:
            raise error

        container = mocker.MagicMock()
        container.execute_item_batch = execute_item_batch
        mocker.patch("library_provider_azure.unit_of_work.AzureClients.container", return_value=container)
