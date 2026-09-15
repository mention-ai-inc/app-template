from collections.abc import Mapping
from dataclasses import dataclass

from library.application.ports.operators import Operator
from library.infrastructure.control_plane import OperatorNotAuthenticatedError

LOCAL_OPERATOR_HEADER = "x-local-operator"
LOCAL_CALLER_IDENTITY = "operator@local.invalid"


@dataclass
class LocalOperatorAuth:
    identity: str = LOCAL_CALLER_IDENTITY

    async def authenticate(self, *, headers: Mapping[str, str]) -> Operator:
        email = headers.get(LOCAL_OPERATOR_HEADER, "")
        if not email:
            raise OperatorNotAuthenticatedError(f"{LOCAL_OPERATOR_HEADER} is absent")
        return Operator(subject=f"local:{email}", email=email)

    async def caller_identity(self) -> str:
        return self.identity
