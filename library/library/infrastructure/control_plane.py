from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType


def JobExecutionNotFoundError(execution_id: str) -> InfrastructureError:
    return InfrastructureError(
        error_type=InfrastructureErrorType.NOT_FOUND_ERROR, message=f"No job execution called {execution_id}"
    )


def JobNotFoundError(job_name: str) -> InfrastructureError:
    return InfrastructureError(error_type=InfrastructureErrorType.NOT_FOUND_ERROR, message=f"No job called {job_name}")


def OperatorNotAuthenticatedError(reason: str) -> InfrastructureError:
    return InfrastructureError(
        error_type=InfrastructureErrorType.OAUTH_ERROR,
        message=f"The caller is not an authenticated operator: {reason}",
        public_message="Not authenticated",
    )
