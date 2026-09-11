from typing import Any

from pydantic import BaseModel, model_validator

from library.domain.errors import DomainError, DomainErrorType
from library.domain.value_objects.core import EnumValueObject, StringValueObject

USER_PREFIX = "user_"
ORGANIZATION_PREFIX = "org_"


class UserID(StringValueObject):
    def __new__(cls, value: str) -> "UserID":
        if not value.startswith(USER_PREFIX):
            raise DomainError(
                error_type=DomainErrorType.VALIDATION_ERROR,
                message=f"User ID must start with 'user_', which is the format for Clerk user IDs. Got: {value}",
            )
        return super().__new__(cls, value)


class OrganizationID(StringValueObject):
    def __new__(cls, value: str) -> "OrganizationID":
        if not value.startswith(ORGANIZATION_PREFIX):
            raise DomainError(
                error_type=DomainErrorType.VALIDATION_ERROR,
                message=f"Organization ID must start with 'org_', which is the format for Clerk organization IDs. Got: {value}",
            )
        return super().__new__(cls, value)


class UserRole(EnumValueObject):
    ADMIN = "admin"
    MEMBER = "member"


class OrganizationPublicMetadata(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def remove_none(cls, values: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in values.items() if value is not None}


class OrganizationPrivateMetadata(BaseModel):
    pass


class UserPublicMetadata(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def none_is_empty(cls, values: dict[str, Any] | None) -> dict[str, Any]:
        if values is None:
            return {}
        return values


class UserPrivateMetadata(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def none_is_empty(cls, values: dict[str, Any] | None) -> dict[str, Any]:
        if values is None:
            return {}
        return values
