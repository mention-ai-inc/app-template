import pytest
from google.api_core.exceptions import Aborted, DeadlineExceeded, InvalidArgument, ServiceUnavailable
from pytest_mock import MockerFixture

from library.application.errors import ApplicationError, ApplicationErrorType
from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType
from library.providers.gcp.unit_of_work import gcp_unit_of_work, get_current_gcp_transaction
from tests.providers.gcp.mocks import patch_firestore_transaction, patch_firestore_transactions


def test_get_current_uow_outside_context_raises_environment_error() -> None:
    with pytest.raises(InfrastructureError) as exc_info:
        get_current_gcp_transaction()

    assert exc_info.value.error_type == InfrastructureErrorType.ENVIRONMENT_ERROR


async def test_get_current_uow_inside_context_returns_transaction(mocker: MockerFixture) -> None:
    transaction = patch_firestore_transaction(mocker)

    async with gcp_unit_of_work():
        uow = get_current_gcp_transaction()

    assert uow is transaction


async def test_successful_context_commits_once_without_retry_and_does_not_rollback(
    mocker: MockerFixture,
) -> None:
    transaction = patch_firestore_transaction(mocker)

    async with gcp_unit_of_work():
        pass

    transaction._begin.assert_awaited_once()
    commit = transaction._client._firestore_api.commit
    commit.assert_awaited_once()
    assert commit.await_args.kwargs["retry"] is None
    transaction._rollback.assert_not_awaited()


async def test_exception_in_body_calls_rollback_and_reraises(mocker: MockerFixture) -> None:
    transaction = patch_firestore_transaction(mocker)

    with pytest.raises(RuntimeError, match="boom"):
        async with gcp_unit_of_work():
            raise RuntimeError("boom")

    transaction._rollback.assert_awaited_once()
    transaction._client._firestore_api.commit.assert_not_awaited()


async def test_aborted_maps_to_transaction_conflict(mocker: MockerFixture) -> None:
    transaction = patch_firestore_transaction(mocker)

    with pytest.raises(ApplicationError) as exc_info:
        async with gcp_unit_of_work():
            raise Aborted("conflict")

    assert exc_info.value.error_type == ApplicationErrorType.TRANSACTION_CONFLICT
    transaction._rollback.assert_awaited_once()


async def test_invalid_argument_maps_to_cloud_error_not_transaction_conflict(
    mocker: MockerFixture,
) -> None:
    transaction = patch_firestore_transaction(mocker)

    with pytest.raises(InfrastructureError) as exc_info:
        async with gcp_unit_of_work():
            raise InvalidArgument("transaction too big")

    assert exc_info.value.error_type == InfrastructureErrorType.CLOUD_ERROR
    assert "transaction too big" in exc_info.value.message
    transaction._rollback.assert_awaited_once()


async def test_expired_transaction_invalid_argument_maps_to_transaction_conflict(
    mocker: MockerFixture,
) -> None:
    transaction = patch_firestore_transaction(mocker)

    with pytest.raises(ApplicationError) as exc_info:
        async with gcp_unit_of_work():
            raise InvalidArgument("400 The referenced transaction has expired or is no longer valid.")

    assert exc_info.value.error_type == ApplicationErrorType.TRANSACTION_CONFLICT
    transaction._rollback.assert_awaited_once()


async def test_service_unavailable_on_commit_maps_to_transaction_conflict(mocker: MockerFixture) -> None:
    transaction = patch_firestore_transaction(mocker)
    transaction._client._firestore_api.commit.side_effect = ServiceUnavailable("503 connection reset")

    with pytest.raises(ApplicationError) as exc_info:
        async with gcp_unit_of_work():
            pass

    assert exc_info.value.error_type == ApplicationErrorType.TRANSACTION_CONFLICT
    transaction._rollback.assert_awaited_once()


async def test_deadline_exceeded_on_commit_maps_to_transaction_conflict(mocker: MockerFixture) -> None:
    transaction = patch_firestore_transaction(mocker)
    transaction._client._firestore_api.commit.side_effect = DeadlineExceeded("504 deadline exceeded")

    with pytest.raises(ApplicationError) as exc_info:
        async with gcp_unit_of_work():
            pass

    assert exc_info.value.error_type == ApplicationErrorType.TRANSACTION_CONFLICT


async def test_rollback_failure_does_not_mask_original_error(mocker: MockerFixture) -> None:
    transaction = patch_firestore_transaction(mocker)
    transaction._client._firestore_api.commit.side_effect = Aborted("conflict")
    transaction._rollback.side_effect = InvalidArgument("rollback on closed transaction")

    with pytest.raises(ApplicationError) as exc_info:
        async with gcp_unit_of_work():
            pass

    assert exc_info.value.error_type == ApplicationErrorType.TRANSACTION_CONFLICT


async def test_rollback_skipped_when_transaction_not_in_progress(mocker: MockerFixture) -> None:
    transaction = patch_firestore_transaction(mocker)
    transaction.in_progress = False
    transaction._begin.side_effect = ServiceUnavailable("503 begin failed")

    with pytest.raises(ApplicationError) as exc_info:
        async with gcp_unit_of_work():
            pass

    assert exc_info.value.error_type == ApplicationErrorType.TRANSACTION_CONFLICT
    transaction._rollback.assert_not_awaited()


async def test_other_exception_passes_through_unchanged(mocker: MockerFixture) -> None:
    patch_firestore_transaction(mocker)

    class CustomError(Exception):
        pass

    with pytest.raises(CustomError):
        async with gcp_unit_of_work():
            raise CustomError("specific")


async def test_uow_is_unset_after_normal_exit(mocker: MockerFixture) -> None:
    patch_firestore_transaction(mocker)

    async with gcp_unit_of_work():
        pass

    with pytest.raises(InfrastructureError) as exc_info:
        get_current_gcp_transaction()
    assert exc_info.value.error_type == InfrastructureErrorType.ENVIRONMENT_ERROR


async def test_uow_is_unset_after_exception(mocker: MockerFixture) -> None:
    patch_firestore_transaction(mocker)

    with pytest.raises(RuntimeError):
        async with gcp_unit_of_work():
            raise RuntimeError("boom")

    with pytest.raises(InfrastructureError) as exc_info:
        get_current_gcp_transaction()
    assert exc_info.value.error_type == InfrastructureErrorType.ENVIRONMENT_ERROR


async def test_nested_contexts_restore_outer_uow_on_inner_exit(mocker: MockerFixture) -> None:
    outer_transaction, inner_transaction = patch_firestore_transactions(mocker, count=2)

    async with gcp_unit_of_work():
        assert get_current_gcp_transaction() is outer_transaction
        async with gcp_unit_of_work():
            assert get_current_gcp_transaction() is inner_transaction
        assert get_current_gcp_transaction() is outer_transaction
