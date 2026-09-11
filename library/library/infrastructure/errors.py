import logging
from enum import StrEnum

from library.logs import SIMPLE_LOGGER_NAME

logger = logging.getLogger(SIMPLE_LOGGER_NAME)


class InfrastructureErrorType(StrEnum):
    CLOUD_ERROR = "CloudError"
    NOT_FOUND_ERROR = "NotFoundError"
    OAUTH_ERROR = "OAuthError"
    QUERY_ERROR = "QueryError"
    VALIDATION_ERROR = "ValidationError"
    VECTOR_INDEX_ERROR = "VectorIndexError"
    INTEGRATION_ERROR = "IntegrationError"
    INTEGRATION_AUTH_ERROR = "IntegrationAuthError"
    ENVIRONMENT_ERROR = "EnvironmentError"
    INELIGIBLE_EVENT = "IneligibleEvent"
    INELIGIBLE_COMMAND = "IneligibleCommand"
    TRANSACTION_CONFLICT = "TransactionConflict"


class InfrastructureError(Exception):
    def __init__(self, *, error_type: InfrastructureErrorType, message: str, public_message: str | None = None) -> None:
        self.error_type = error_type
        self.message = message
        self.public_message = public_message or message
        super().__init__(f"InfrastructureError ({error_type}): {message}")

    @property
    def private_message(self) -> str:
        return self.message
