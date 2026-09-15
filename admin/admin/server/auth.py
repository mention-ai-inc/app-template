import os

from fastapi import Request

from library.application.audit.context import set_actor
from library.application.ports.operators import Operator
from library.domain.audit.actor import AuditActor, AuditActorType
from library.infrastructure.errors import InfrastructureError
from library.presentation.errors import PresentationError, PresentationErrorType
from library.providers.registry import get_cloud_provider

__all__ = ["Operator", "require_operator"]


async def require_operator(request: Request) -> Operator:
    try:
        operator = await get_cloud_provider().operator_auth().authenticate(headers=request.headers)
    except InfrastructureError as error:
        raise PresentationError(
            error_type=PresentationErrorType.AUTHENTICATION_ERROR,
            message=error.private_message,
            public_message=error.public_message,
        ) from error

    if operator.email not in _staff_allowlist():
        raise PresentationError(
            error_type=PresentationErrorType.AUTHORIZATION_ERROR,
            message=f"{operator.email} is not on the staff allowlist.",
            public_message="This identity is not authorized for admin operations.",
        )

    set_actor(
        AuditActor(
            actor_type=AuditActorType.OPERATOR,
            actor_id=operator.subject,
            actor_email=operator.email,
            actor_role=None,
            impersonated_by=None,
        )
    )
    return operator


def _staff_allowlist() -> frozenset[str]:
    return frozenset(entry.strip() for entry in os.getenv("STAFF_ALLOWLIST", "").split(",") if entry.strip())
