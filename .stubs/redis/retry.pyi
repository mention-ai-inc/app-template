from collections.abc import Callable
from typing import Any

from redis.backoff import AbstractBackoff


class Retry:
    def __init__(self, backoff: AbstractBackoff, retries: int) -> None: ...
    def call_with_retry[T](self, do: Callable[[], T], fail: Callable[[Exception], Any]) -> T: ...
