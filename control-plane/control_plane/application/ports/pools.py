from typing import Protocol

from fastapi import FastAPI


class IPoolDriver(Protocol):
    async def __call__(self, *, app: FastAPI, routes: dict[str, str]) -> None: ...
