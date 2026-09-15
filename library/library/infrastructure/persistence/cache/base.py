import logging
import os

from redis.asyncio import ConnectionPool as AsyncConnectionPool
from redis.asyncio import Redis as AsyncRedis
from redis.asyncio.connection import Connection as AsyncConnection
from redis.asyncio.connection import SSLConnection as AsyncSSLConnection
from redis.asyncio.retry import Retry as AsyncRetry
from redis.backoff import ExponentialBackoff
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from library.application.ports.cache import CacheKey, get_global_cache_key, get_organizational_cache_key
from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType
from library.logs import SIMPLE_LOGGER_NAME

__all__ = [
    "AsyncCache",
    "CacheKey",
    "aclose_cache_pool",
    "get_global_cache_key",
    "get_organizational_cache_key",
]

logger = logging.getLogger(SIMPLE_LOGGER_NAME)

DEFAULT_PORT = 6379
DEFAULT_TLS_PORT = 6380
SOCKET_TIMEOUT_SECONDS = 2.0
SOCKET_CONNECT_TIMEOUT_SECONDS = 2.0
HEALTH_CHECK_INTERVAL_SECONDS = 30
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_BASE_SECONDS = 0.05
RETRY_BACKOFF_CAP_SECONDS = 0.5
RETRYABLE_ERRORS: tuple[type[Exception], ...] = (RedisConnectionError, RedisTimeoutError)

_pool: AsyncConnectionPool | None = None


class AsyncCache(AsyncRedis):
    def __init__(self) -> None:
        super().__init__(connection_pool=_get_pool())


async def aclose_cache_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None


def _get_pool() -> AsyncConnectionPool:
    global _pool
    if _pool is None:
        host, port, password, uses_tls = _redis_connection_settings()
        _pool = AsyncConnectionPool(
            connection_class=AsyncSSLConnection if uses_tls else AsyncConnection,
            host=host,
            port=port,
            db=0,
            decode_responses=False,
            password=password,
            socket_timeout=SOCKET_TIMEOUT_SECONDS,
            socket_connect_timeout=SOCKET_CONNECT_TIMEOUT_SECONDS,
            health_check_interval=HEALTH_CHECK_INTERVAL_SECONDS,
            retry=AsyncRetry(backoff=_backoff(), retries=RETRY_ATTEMPTS),
            retry_on_timeout=True,
            retry_on_error=list(RETRYABLE_ERRORS),
        )
    return _pool


def _backoff() -> ExponentialBackoff:
    return ExponentialBackoff(base=RETRY_BACKOFF_BASE_SECONDS, cap=RETRY_BACKOFF_CAP_SECONDS)


def _redis_connection_settings() -> tuple[str, int, str, bool]:
    host = os.getenv("REDIS_HOST", "localhost")
    uses_tls = os.getenv("REDIS_TLS", "").lower() in {"1", "true", "yes"}
    port = int(os.getenv("REDIS_PORT") or (DEFAULT_TLS_PORT if uses_tls else DEFAULT_PORT))
    password = os.getenv("REDIS_PASSWORD")
    if password is None:
        raise InfrastructureError(
            error_type=InfrastructureErrorType.ENVIRONMENT_ERROR,
            message="REDIS_PASSWORD must be set to use cache",
        )
    return host, port, password, uses_tls
