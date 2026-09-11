from library._testutils.cache import FakeAsyncCache
from library.infrastructure.persistence.cache.base import CacheKey


async def test_setnx_writes_when_key_absent_and_reports_true() -> None:
    cache = FakeAsyncCache()

    written = await cache.setnx(__key(), b"hello")

    assert written is True


async def test_setnx_does_not_overwrite_when_key_already_present() -> None:
    cache = FakeAsyncCache()
    await cache.setnx(__key(), b"100")

    written = await cache.setnx(__key(), b"200")

    assert written is False
    assert await cache.incrby(__key(), 0) == 100  # original value preserved


async def test_incrby_initialises_missing_key_to_amount() -> None:
    cache = FakeAsyncCache()

    new_value = await cache.incrby(__key(), 5)

    assert new_value == 5


async def test_incrby_accumulates_across_calls() -> None:
    cache = FakeAsyncCache()
    await cache.incrby(__key(), 3)

    new_value = await cache.incrby(__key(), 4)

    assert new_value == 7


async def test_incrby_combines_with_setnx_seed_value() -> None:
    cache = FakeAsyncCache()
    await cache.setnx(__key(), b"10")

    new_value = await cache.incrby(__key(), 5)

    assert new_value == 15


async def test_sadd_adds_new_members_and_reports_count() -> None:
    cache = FakeAsyncCache()

    added = await cache.sadd(__key(), b"a", b"b", b"c")

    assert added == 3
    assert await cache.smembers(__key()) == {b"a", b"b", b"c"}


async def test_sadd_skips_members_already_present() -> None:
    cache = FakeAsyncCache()
    await cache.sadd(__key(), b"a", b"b")

    added = await cache.sadd(__key(), b"a", b"c")

    assert added == 1
    assert await cache.smembers(__key()) == {b"a", b"b", b"c"}


async def test_smembers_returns_empty_set_when_key_absent() -> None:
    cache = FakeAsyncCache()

    assert await cache.smembers(__key()) == set()


def __key() -> CacheKey:
    return CacheKey("test:key")
