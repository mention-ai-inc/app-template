from typing import Protocol

from fastapi import Request
from pydantic import BaseModel


class IDocumentChangeFeed[DataT: BaseModel](Protocol):
    async def __call__(self, request: Request) -> DataT | None: ...
