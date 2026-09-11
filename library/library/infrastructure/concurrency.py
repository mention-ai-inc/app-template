import asyncio
from collections.abc import Awaitable
from typing import Literal, overload


@overload
async def map_limit[T](
    *coros: Awaitable[T], limit: int, return_exceptions: Literal[True]
) -> list[T | BaseException]: ...
@overload
async def map_limit[T](*coros: Awaitable[T], limit: int, return_exceptions: Literal[False] = ...) -> list[T]: ...
@overload
async def map_limit[T](*coros: Awaitable[T], limit: int) -> list[T]: ...


async def map_limit[T](
    *coros: Awaitable[T], limit: int, return_exceptions: bool = False
) -> list[T] | list[T | BaseException]:
    semaphore = asyncio.Semaphore(limit)

    async def bounded_coro(coro: Awaitable[T]) -> T:
        async with semaphore:
            return await coro

    tasks = [bounded_coro(coro) for coro in coros]
    return await asyncio.gather(*tasks, return_exceptions=return_exceptions)
