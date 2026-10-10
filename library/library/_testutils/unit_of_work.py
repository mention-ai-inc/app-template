from collections.abc import AsyncGenerator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from contextvars import ContextVar


class FakeTransactionState:
    """Per-block state for the active fake transaction.

    Mirrors the read-before-write constraint every provider's transaction enforces:
    once a write has been buffered, any subsequent read in the same block is a
    read-after-write error. `InMemoryRepository` consults this to fail tests that
    interleave reads and writes inside a `unit_of_work()` (the most common bug
    we ship — see `.claude/rules/read-after-write.md`).
    """

    def __init__(self) -> None:
        self.has_written = False


_active_transaction: ContextVar[FakeTransactionState | None] = ContextVar("fake_unit_of_work_transaction", default=None)


def active_transaction() -> FakeTransactionState | None:
    """The current fake transaction, or `None` when no `FakeUnitOfWork` is open.

    This is the test-side analog of production's `get_current_uow()` — it lets a
    repository fake know whether it is running inside a transaction.
    """
    return _active_transaction.get()


@asynccontextmanager
async def in_uow() -> AsyncGenerator[None]:
    """Async context manager for a single fake transaction block in tests."""
    uow = FakeUnitOfWork()
    async with uow():
        yield


class FakeUnitOfWork:
    """No-op async context manager satisfying `IUnitOfWork`.

    Tracks `enter_count` (how many times the context manager was entered) so
    tests can assert that a use case wrapped its work in a transaction.

    While entered, it publishes a `FakeTransactionState` via a `ContextVar` —
    exactly how production's `unit_of_work()` publishes the real transaction via
    `get_current_uow()`. `InMemoryRepository` reads that state to enforce the
    read-before-write rule, so read-after-write bugs fail in tests
    instead of only in production.
    """

    def __init__(self) -> None:
        self.enter_count = 0

    def __call__(self) -> AbstractAsyncContextManager[None]:
        return self.__enter()

    @asynccontextmanager
    async def __enter(self) -> AsyncGenerator[None]:
        self.enter_count += 1
        token = _active_transaction.set(FakeTransactionState())
        try:
            yield
        finally:
            _active_transaction.reset(token)
