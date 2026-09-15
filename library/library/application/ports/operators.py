from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Operator:
    subject: str
    email: str


class IOperatorAuth(Protocol):
    async def authenticate(self, *, headers: Mapping[str, str]) -> Operator: ...

    async def caller_identity(self) -> str: ...
