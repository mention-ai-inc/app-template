from collections.abc import Generator

import pytest

from library.infrastructure.errors import InfrastructureError
from library.infrastructure.unit_of_work import get_current_uow, unit_of_work
from library.providers.local.database import LocalTransaction
from library.providers.local.provider import PROVIDER as LOCAL_PROVIDER
from library.providers.registry import get_cloud_provider, reset_cloud_provider, set_cloud_provider


@pytest.fixture(autouse=True)
def _local_provider() -> Generator[None]:  # pyright: ignore[reportUnusedFunction]
    set_cloud_provider(LOCAL_PROVIDER)
    yield
    reset_cloud_provider()


def test_the_generic_seam_resolves_the_selected_provider() -> None:
    assert get_cloud_provider().name == "local"


async def test_unit_of_work_opens_the_providers_transaction() -> None:
    async with unit_of_work():
        assert isinstance(get_current_uow(), LocalTransaction)


async def test_the_transaction_is_gone_once_the_block_closes() -> None:
    async with unit_of_work():
        pass

    with pytest.raises(InfrastructureError):
        get_current_uow()


def test_asking_for_a_transaction_outside_a_block_raises() -> None:
    with pytest.raises(InfrastructureError):
        get_current_uow()
