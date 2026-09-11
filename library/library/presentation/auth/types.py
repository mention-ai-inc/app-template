import os
from typing import Any

from pydantic import BaseModel, field_validator, model_validator

from library.domain.value_objects.common import Service
from library.domain.value_objects.users import (
    OrganizationID,
    OrganizationPublicMetadata,
    UserID,
    UserRole,
)
from library.infrastructure.users import ClerkRole


class AuthenticatedUser(BaseModel):
    token: str
    uid: UserID
    organization_id: OrganizationID
    clerk_role: ClerkRole
    organization_public_metadata: OrganizationPublicMetadata
    impersonating_service: Service | None = None

    @property
    def user_role(self) -> UserRole:
        return self.clerk_role.get_user_role()

    @field_validator("organization_public_metadata", mode="before")
    def select_active_feature_environment(cls, values: dict[str, Any]) -> dict[str, Any]:
        return values.get(os.getenv("FEATURE_ENVIRONMENT", ""), {})  # in production, "" is the top level key

    @model_validator(mode="before")
    def user_is_admin_of_own_org_when_not_set(cls, values: dict[str, Any]) -> dict[str, Any]:
        if values.get("organization_id") is None:
            values["organization_id"] = values["uid"]
            values["clerk_role"] = ClerkRole.ADMIN

        return values
