from enum import StrEnum


class DomainErrorType(StrEnum):
    VALIDATION_ERROR = "ValidationError"
    QUOTA_ERROR = "QuotaError"


class DomainError(Exception):
    def __init__(
        self,
        *,
        message: str,
        public_message: str | None = None,
        error_type: DomainErrorType = DomainErrorType.VALIDATION_ERROR,
    ) -> None:
        self.message = message
        self.public_message = public_message or message
        self.error_type = error_type
        super().__init__(f"DomainError: {error_type} ({message})")

    @property
    def private_message(self) -> str:
        return self.message
