from contextlib import AbstractAsyncContextManager
from typing import Protocol


class IUnitOfWork(Protocol):
    def __call__(self) -> AbstractAsyncContextManager[None]: ...
