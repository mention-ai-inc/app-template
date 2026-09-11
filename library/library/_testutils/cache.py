from fnmatch import fnmatch
from typing import Any, cast

from library.infrastructure.persistence.cache.base import AsyncCache


class FakePipeline:
    def __init__(self, cache: "FakeAsyncCache") -> None:
        self._cache = cache
        self._queued: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    async def __aenter__(self) -> "FakePipeline":
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        return None

    async def execute(self) -> list[Any]:
        queued, self._queued = self._queued, []
        return [await getattr(self._cache, command)(*args, **kwargs) for command, args, kwargs in queued]

    def __getattr__(self, command: str) -> Any:
        def queue_command(*args: Any, **kwargs: Any) -> "FakePipeline":
            self._queued.append((command, args, kwargs))
            return self

        return queue_command


class FakeAsyncCache(AsyncCache):
    """In-memory `AsyncCache` for service-level tests.

    Subclasses `AsyncCache` (a `redis.asyncio.Redis` subclass) but skips
    `super().__init__()` so no Redis connection is opened. Implements only the
    subset of methods that production services call against the cache from the
    paths under test (string, hash, set, and sorted-set commands plus `scan`
    and `pipeline`); other inherited methods continue to delegate to the Redis
    client and would fail without a connection — that failure is the desired
    signal to extend this fake. `pipeline` returns a `FakePipeline` that queues
    commands and replays them sequentially on `execute`, without transaction
    semantics.
    """

    def __init__(self) -> None:
        self._values: dict[str, bytes] = {}
        self._sets: dict[str, set[bytes]] = {}
        self._hashes: dict[str, dict[bytes, bytes]] = {}
        self._zsets: dict[str, dict[bytes, float]] = {}
        self._ttls: dict[str, int] = {}

    def pipeline(self, transaction: bool = False, shard_hint: Any = None) -> FakePipeline:  # noqa: ARG002 # pyright: ignore[reportIncompatibleMethodOverride]
        return FakePipeline(self)

    async def get(self, name: Any) -> bytes | None:
        key = self.__to_key(name)
        return self._values.get(key)

    async def delete(self, *names: Any) -> int:
        removed = 0
        for name in names:
            key = self.__to_key(name)
            if key in self._values:
                del self._values[key]
                removed += 1
            if key in self._sets:
                del self._sets[key]
                removed += 1
            if key in self._hashes:
                del self._hashes[key]
                removed += 1
            if key in self._zsets:
                del self._zsets[key]
                removed += 1
            self._ttls.pop(key, None)
        return removed

    async def set(
        self,
        name: str,
        value: bytes,
        /,
        *,
        ex: int | None = None,  # noqa: ARG002 - TTL not modeled in-memory
        px: int | None = None,  # noqa: ARG002
        nx: bool | None = None,
        xx: bool | None = None,  # noqa: ARG002
    ) -> bool | None:
        key = self.__to_key(name)
        if nx:
            if key in self._values:
                return None
            self._values[key] = value
            return True

        if xx and key not in self._values:
            return None

        self._values[key] = value
        return True

    async def expire(self, name: Any, time: Any, **kwargs: Any) -> bool:  # noqa: ARG002
        self._ttls[self.__to_key(name)] = int(time)
        return True

    async def ttl(self, name: Any) -> int:
        key = self.__to_key(name)
        if key in self._ttls:
            return self._ttls[key]
        if key in self._values or key in self._sets or key in self._hashes or key in self._zsets:
            return -1
        return -2

    async def setnx(
        self,
        name: bytes | str | memoryview,
        value: bytes | bytearray | memoryview | str | int | float,
        **kwargs: Any,  # noqa: ARG002
    ) -> bool:
        key = self.__to_key(name)
        if key in self._values:
            return False
        self._values[key] = self.__to_bytes(value)
        return True

    async def incrby(
        self,
        name: bytes | str | memoryview,
        amount: int = 1,
    ) -> int:
        key = self.__to_key(name)
        current = int(self._values.get(key, b"0"))
        new_value = current + amount
        self._values[key] = str(new_value).encode()
        return new_value

    async def eval(
        self,
        script: Any,  # noqa: ARG002
        numkeys: Any,  # noqa: ARG002
        *keys_and_args: Any,
    ) -> Any:
        key_bytes = keys_and_args[0]
        member = keys_and_args[1]
        key = self.__to_key(key_bytes)
        member_bytes = member if isinstance(member, bytes) else self.__to_bytes(member)
        bucket = self._sets.setdefault(key, set())
        bucket.add(member_bytes)
        return len(bucket)

    async def srem(self, name: Any, *values: Any) -> int:
        key = self.__to_key(name)
        bucket = self._sets.get(key)
        if bucket is None:
            return 0
        removed = 0
        for value in values:
            value_bytes = value if isinstance(value, bytes) else self.__to_bytes(value)
            if value_bytes in bucket:
                bucket.remove(value_bytes)
                removed += 1
        return removed

    async def smembers(self, name: Any) -> "set[bytes]":
        key = self.__to_key(name)
        bucket = self._sets.get(key, cast(set[bytes], set()))
        return set(bucket)

    async def smismember(self, name: Any, *values: Any) -> list[bool]:
        key = self.__to_key(name)
        bucket = self._sets.get(key, cast(set[bytes], set()))
        return [self.__to_bytes(value) in bucket for value in values]

    async def sadd(self, name: Any, *values: Any) -> int:  # pyright: ignore[reportIncompatibleMethodOverride]
        key = self.__to_key(name)
        bucket = self._sets.setdefault(key, set())
        added = 0
        for value in values:
            value_bytes = value if isinstance(value, bytes) else self.__to_bytes(value)
            if value_bytes not in bucket:
                bucket.add(value_bytes)
                added += 1
        return added

    async def hmget(self, name: Any, keys: Any, *args: Any) -> list[bytes | None]:  # pyright: ignore[reportIncompatibleMethodOverride]
        cache_key = self.__to_key(name)
        bucket = self._hashes.get(cache_key, {})
        fields: tuple[Any, ...] = (*keys, *args) if isinstance(keys, list | tuple) else (keys, *args)
        return [bucket.get(self.__to_bytes(field)) for field in fields]

    async def hgetall(self, name: Any) -> dict[bytes, bytes]:  # pyright: ignore[reportIncompatibleMethodOverride]
        cache_key = self.__to_key(name)
        return dict(self._hashes.get(cache_key, {}))

    async def hset(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        name: Any,
        key: Any | None = None,
        value: Any | None = None,
        mapping: dict[Any, Any] | None = None,
        items: list[Any] | None = None,  # noqa: ARG002
    ) -> int:
        cache_key = self.__to_key(name)
        bucket = self._hashes.setdefault(cache_key, {})
        updates: dict[Any, Any] = {}
        if mapping is not None:
            updates.update(mapping)
        if key is not None and value is not None:
            updates[key] = value

        added = 0
        for field, field_value in updates.items():
            field_bytes = self.__to_bytes(field)
            if field_bytes not in bucket:
                added += 1
            bucket[field_bytes] = self.__to_bytes(field_value)
        return added

    async def hdel(self, name: Any, *keys: Any) -> int:  # pyright: ignore[reportIncompatibleMethodOverride]
        cache_key = self.__to_key(name)
        bucket = self._hashes.get(cache_key)
        if bucket is None:
            return 0

        removed = 0
        for field in keys:
            field_bytes = self.__to_bytes(field)
            if field_bytes in bucket:
                del bucket[field_bytes]
                removed += 1
        return removed

    async def hget(self, name: Any, key: Any) -> bytes | None:  # pyright: ignore[reportIncompatibleMethodOverride]
        cache_key = self.__to_key(name)
        return self._hashes.get(cache_key, {}).get(self.__to_bytes(key))

    async def zadd(self, name: Any, mapping: dict[Any, float], **kwargs: Any) -> int:  # noqa: ARG002 # pyright: ignore[reportIncompatibleMethodOverride]
        cache_key = self.__to_key(name)
        bucket = self._zsets.setdefault(cache_key, {})
        added = 0
        for member, score in mapping.items():
            member_bytes = self.__to_bytes(member)
            if member_bytes not in bucket:
                added += 1
            bucket[member_bytes] = float(score)
        return added

    async def zincrby(self, name: Any, amount: float, value: Any) -> float:
        cache_key = self.__to_key(name)
        bucket = self._zsets.setdefault(cache_key, {})
        member_bytes = self.__to_bytes(value)
        bucket[member_bytes] = bucket.get(member_bytes, 0.0) + amount
        return bucket[member_bytes]

    async def zscore(self, name: Any, value: Any) -> float | None:
        cache_key = self.__to_key(name)
        return self._zsets.get(cache_key, {}).get(self.__to_bytes(value))

    async def zrem(self, name: Any, *values: Any) -> int:
        cache_key = self.__to_key(name)
        bucket = self._zsets.get(cache_key)
        if bucket is None:
            return 0
        removed = 0
        for value in values:
            member_bytes = self.__to_bytes(value)
            if member_bytes in bucket:
                del bucket[member_bytes]
                removed += 1
        if not bucket:
            del self._zsets[cache_key]
        return removed

    async def zremrangebyscore(self, name: Any, min_score: Any, max_score: Any) -> int:  # pyright: ignore[reportIncompatibleMethodOverride]
        cache_key = self.__to_key(name)
        bucket = self._zsets.get(cache_key)
        if bucket is None:
            return 0
        lower = self.__to_score_bound(min_score)
        upper = self.__to_score_bound(max_score)
        members_to_remove = [member for member, score in bucket.items() if lower <= score <= upper]
        for member in members_to_remove:
            del bucket[member]
        if not bucket:
            del self._zsets[cache_key]
        return len(members_to_remove)

    async def zrevrange(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        name: Any,
        start: int,
        end: int,
        withscores: bool = False,
        **kwargs: Any,  # noqa: ARG002
    ) -> list[Any]:
        cache_key = self.__to_key(name)
        bucket = self._zsets.get(cache_key, {})
        ordered = sorted(bucket.items(), key=lambda item: (item[1], item[0]), reverse=True)
        stop = len(ordered) if end == -1 else end + 1
        window = ordered[start:stop]
        if withscores:
            return list(window)
        return [member for member, _ in window]

    async def scan(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        cursor: int = 0,  # noqa: ARG002
        match: str | None = None,
        count: int | None = None,  # noqa: ARG002
        **kwargs: Any,  # noqa: ARG002
    ) -> tuple[int, list[bytes]]:
        all_keys = [*self._values, *self._sets, *self._hashes, *self._zsets]
        matching = [key.encode() for key in all_keys if match is None or fnmatch(key, match)]
        return 0, matching

    @staticmethod
    def __to_key(name: bytes | str | memoryview) -> str:
        if isinstance(name, str):
            return name
        if isinstance(name, memoryview):
            return bytes(name).decode()
        return name.decode()

    @staticmethod
    def __to_bytes(value: bytes | bytearray | memoryview | str | int | float) -> bytes:
        if isinstance(value, bytes):
            return value
        if isinstance(value, bytearray | memoryview):
            return bytes(value)
        return str(value).encode()

    @staticmethod
    def __to_score_bound(bound: Any) -> float:
        if isinstance(bound, bytes):
            return float(bound.decode())
        return float(bound)
