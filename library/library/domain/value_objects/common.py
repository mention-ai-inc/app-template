from pydantic import BaseModel

from library.domain.errors import DomainError, DomainErrorType
from library.domain.value_objects.core import DictValueObject, EnumValueObject, StringValueObject


class Service(EnumValueObject):
    NOTES = "notes"


class EntitySet[KeyT: str, EntityT: BaseModel](DictValueObject[KeyT, EntityT]):
    def __getitem__(self, key: KeyT) -> EntityT:
        try:
            return super().__getitem__(key)
        except KeyError:
            raise DomainError(
                error_type=DomainErrorType.VALIDATION_ERROR,
                message=f"Entity with key {key} not found",
                public_message="Entity not found.",
            )


class PresignedURL(StringValueObject):
    EXPECTED_DOMAIN = "storage.googleapis.com"

    def __new__(cls, value: str) -> "PresignedURL":
        if cls.EXPECTED_DOMAIN not in value:
            raise DomainError(message=f"Presigned URL must be a Google Cloud Storage URL. Got: {value}")
        return super().__new__(cls, value)
