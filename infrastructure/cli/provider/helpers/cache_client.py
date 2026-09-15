import os
from importlib import import_module
from typing import Any

import redis

SSL_CONNECTION: Any = import_module("redis.connection").SSLConnection

REDIS_HOST = os.environ["REDIS_HOST"]
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6380"))
REDIS_PASSWORD = os.environ["REDIS_PASSWORD"]


def tls_client(*, decode_responses: bool) -> redis.Redis:
    pool = redis.ConnectionPool(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=0,
        decode_responses=decode_responses,
        password=REDIS_PASSWORD,
    )
    transport: Any = pool
    transport.connection_class = SSL_CONNECTION
    return redis.Redis(connection_pool=pool)
