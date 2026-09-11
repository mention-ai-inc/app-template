import asyncio
from typing import Any

import pytest
from redis.asyncio.retry import Retry as AsyncRetry
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from library.infrastructure.persistence.cache import base
from library.infrastructure.persistence.cache.base import (
    HEALTH_CHECK_INTERVAL_SECONDS,
    RETRY_ATTEMPTS,
    RETRY_BACKOFF_CAP_SECONDS,
    RETRYABLE_ERRORS,
    SOCKET_CONNECT_TIMEOUT_SECONDS,
    SOCKET_TIMEOUT_SECONDS,
    AsyncCache,
    aclose_cache_pool,
)


async def test_pool_bounds_socket_connects_reads_and_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    kwargs = __pool_kwargs(monkeypatch)

    assert kwargs["socket_connect_timeout"] == SOCKET_CONNECT_TIMEOUT_SECONDS
    assert kwargs["socket_timeout"] == SOCKET_TIMEOUT_SECONDS


async def test_pool_validates_connections_idle_since_the_last_health_check(monkeypatch: pytest.MonkeyPatch) -> None:
    kwargs = __pool_kwargs(monkeypatch)

    assert kwargs["health_check_interval"] == HEALTH_CHECK_INTERVAL_SECONDS


async def test_pool_marks_timeouts_and_connection_errors_retryable(monkeypatch: pytest.MonkeyPatch) -> None:
    kwargs = __pool_kwargs(monkeypatch)

    assert kwargs["retry_on_timeout"] is True
    assert kwargs["retry_on_error"] == [RedisConnectionError, RedisTimeoutError]
    assert RETRYABLE_ERRORS == (RedisConnectionError, RedisTimeoutError)


async def test_pool_recovers_when_a_blip_clears_before_the_retries_run_out(monkeypatch: pytest.MonkeyPatch) -> None:
    retry = __retry(monkeypatch)
    __capture_backoff(monkeypatch)
    attempts = 0

    async def blip() -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RedisConnectionError("Timeout connecting to server")
        return "value"

    assert await retry.call_with_retry(blip, __swallow) == "value"
    assert attempts == 2


async def test_pool_gives_up_after_a_bounded_number_of_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    retry = __retry(monkeypatch)
    sleeps = __capture_backoff(monkeypatch)
    attempts = 0

    async def timeout() -> None:
        nonlocal attempts
        attempts += 1
        raise RedisTimeoutError("Timeout writing to socket")

    with pytest.raises(RedisTimeoutError):
        await retry.call_with_retry(timeout, __swallow)

    assert attempts == RETRY_ATTEMPTS + 1
    assert len(sleeps) == RETRY_ATTEMPTS
    assert max(sleeps) <= RETRY_BACKOFF_CAP_SECONDS


async def test_pool_does_not_retry_unrelated_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    retry = __retry(monkeypatch)
    __capture_backoff(monkeypatch)
    attempts = 0

    async def fail() -> None:
        nonlocal attempts
        attempts += 1
        raise ValueError("not a connectivity problem")

    with pytest.raises(ValueError):
        await retry.call_with_retry(fail, __swallow)

    assert attempts == 1


async def test_every_cache_in_a_process_shares_one_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    __reset_pool(monkeypatch)

    assert AsyncCache().connection_pool is AsyncCache().connection_pool


async def test_closing_one_cache_leaves_the_shared_pool_usable(monkeypatch: pytest.MonkeyPatch) -> None:
    __reset_pool(monkeypatch)
    cache = AsyncCache()
    pool = cache.connection_pool

    await cache.aclose()

    assert AsyncCache().connection_pool is pool


async def test_closing_the_pool_lets_a_later_event_loop_build_a_fresh_one(monkeypatch: pytest.MonkeyPatch) -> None:
    __reset_pool(monkeypatch)
    pool = AsyncCache().connection_pool

    await aclose_cache_pool()

    assert AsyncCache().connection_pool is not pool


def test_cache_can_be_built_without_a_running_event_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    __reset_pool(monkeypatch)

    with pytest.raises(RuntimeError):
        asyncio.get_running_loop()

    assert AsyncCache().connection_pool is not None


def __reset_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDIS_PASSWORD", "test-password")
    monkeypatch.setattr(base, "_pool", None)


def __pool_kwargs(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    __reset_pool(monkeypatch)
    return AsyncCache().connection_pool.connection_kwargs


def __retry(monkeypatch: pytest.MonkeyPatch) -> AsyncRetry:
    retry = __pool_kwargs(monkeypatch)["retry"]
    assert isinstance(retry, AsyncRetry)
    return retry


def __capture_backoff(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    sleeps: list[float] = []

    async def record(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr("redis.asyncio.retry.sleep", record)
    return sleeps


async def __swallow(_: Exception) -> None:
    return None
