from library._testutils.unit_of_work import FakeUnitOfWork


async def test_enter_count_starts_at_zero() -> None:
    uow = FakeUnitOfWork()

    assert uow.enter_count == 0


async def test_enter_count_increments_on_each_enter() -> None:
    uow = FakeUnitOfWork()

    async with uow():
        pass
    async with uow():
        pass

    assert uow.enter_count == 2


async def test_yields_none() -> None:
    uow = FakeUnitOfWork()

    async with uow() as value:
        assert value is None
