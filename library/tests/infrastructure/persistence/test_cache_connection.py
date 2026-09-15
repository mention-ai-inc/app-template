from collections.abc import Generator

import pytest
from redis.asyncio.connection import Connection as AsyncConnection
from redis.asyncio.connection import SSLConnection as AsyncSSLConnection

from library.infrastructure.persistence.cache import base
from library.infrastructure.persistence.cache.base import AsyncCache


@pytest.fixture(autouse=True)
def _no_pool(monkeypatch: pytest.MonkeyPatch) -> Generator[None]:  # pyright: ignore[reportUnusedFunction]
    monkeypatch.setattr(base, "_pool", None)
    monkeypatch.setenv("REDIS_PASSWORD", "secret")
    monkeypatch.delenv("REDIS_TLS", raising=False)
    monkeypatch.delenv("REDIS_PORT", raising=False)
    yield
    monkeypatch.setattr(base, "_pool", None)


def test_a_plain_cache_speaks_the_default_port_without_tls() -> None:
    pool = AsyncCache().connection_pool

    assert pool.connection_kwargs["port"] == base.DEFAULT_PORT
    assert pool.connection_class is AsyncConnection


def test_a_tls_cache_moves_to_the_tls_port(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDIS_TLS", "true")

    pool = AsyncCache().connection_pool

    assert pool.connection_kwargs["port"] == base.DEFAULT_TLS_PORT
    assert pool.connection_class is AsyncSSLConnection


def test_an_explicit_port_wins_over_both_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDIS_TLS", "true")
    monkeypatch.setenv("REDIS_PORT", "6390")

    pool = AsyncCache().connection_pool

    assert pool.connection_kwargs["port"] == 6390
    assert pool.connection_class is AsyncSSLConnection
