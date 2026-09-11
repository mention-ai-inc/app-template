import os
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from admin.server.audit import AdminAuditor
from admin.server.auth import require_operator
from admin.server.dependencies import get_auditor

router = APIRouter(tags=["Operations"], dependencies=[Depends(require_operator)])

AuditorDependency = Annotated[AdminAuditor, Depends(get_auditor)]

UNLISTED_PATHS = {"/health", "/operations"}


class OperationsResponse(BaseModel):
    environment: str
    commit_sha: str | None
    image_digest: str | None
    operations: list[str]


@router.get("/operations")
async def list_operations(request: Request, auditor: AuditorDependency) -> OperationsResponse:
    async with auditor.operation(operation="operations.list", organization_id=None, parameters={}):
        paths: dict[str, dict[str, object]] = request.app.openapi()["paths"]
        operations = sorted(
            f"{method.upper()} {path}"
            for path, methods in paths.items()
            if path not in UNLISTED_PATHS
            for method in methods
        )
        return OperationsResponse(
            environment=os.getenv("FEATURE_ENVIRONMENT", "") or "production",
            commit_sha=os.getenv("COMMIT_SHA"),
            image_digest=os.getenv("IMAGE_DIGEST"),
            operations=operations,
        )
