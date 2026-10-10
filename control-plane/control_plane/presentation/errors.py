from enum import StrEnum


class PresentationErrorType(StrEnum):
    AUTHENTICATION_ERROR = "AuthenticationError"
    AUTHORIZATION_ERROR = "AuthorizationError"
    QUOTA_ERROR = "QuotaError"


class PresentationError(Exception):
    def __init__(self, *, error_type: PresentationErrorType, message: str, public_message: str | None = None) -> None:
        self.error_type = error_type
        self.message = message
        self.public_message = public_message or message
        super().__init__(f"PresentationError: {error_type} ({message})")

    @property
    def private_message(self) -> str:
        return self.message
