from collections.abc import Awaitable, Callable
from typing import Any

from redis.backoff import AbstractBackoff


class Retry:
    def __init__(self, backoff: AbstractBackoff, retries: int) -> None: ...
    async def call_with_retry[T](
        self, do: Callable[[], Awaitable[T]], fail: Callable[[Exception], Awaitable[Any]]
    ) -> T: ...
