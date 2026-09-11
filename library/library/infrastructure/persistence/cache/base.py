import logging
import os

from redis.asyncio import ConnectionPool as AsyncConnectionPool
from redis.asyncio import Redis as AsyncRedis
from redis.asyncio.retry import Retry as AsyncRetry
from redis.backoff import ExponentialBackoff
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from library.application.cache import CacheKey, get_global_cache_key, get_organizational_cache_key
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
        host, password = _redis_connection_settings()
        _pool = AsyncConnectionPool(
            host=host,
            port=6379,
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


def _redis_connection_settings() -> tuple[str, str]:
    host = os.getenv("REDIS_HOST", "localhost")
    password = os.getenv("REDIS_PASSWORD")
    if password is None:
        raise InfrastructureError(
            error_type=InfrastructureErrorType.ENVIRONMENT_ERROR,
            message="REDIS_PASSWORD must be set to use cache",
        )
    return host, password
