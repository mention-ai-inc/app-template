from enum import StrEnum


class ApplicationErrorType(StrEnum):
    VALIDATION_ERROR = "ValidationError"
    PROCESS_FAILED = "ProcessFailed"
    RESOURCE_NOT_FOUND = "ResourceNotFound"
    TRANSACTION_CONFLICT = "TransactionConflict"


class ApplicationError(Exception):
    def __init__(self, *, error_type: ApplicationErrorType, message: str, public_message: str | None = None) -> None:
        self.error_type = error_type
        self.message = message
        self.public_message = public_message or message
        super().__init__(f"ApplicationError: {error_type} ({message})")

    @property
    def private_message(self) -> str:
        return self.message
