import asyncio
import json
import logging
import os
import random
import time
import traceback
from collections.abc import Callable, Coroutine
from typing import Any

import jwt
import sentry_sdk
from fastapi import HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from pydantic import BaseModel
from pydantic_ai.exceptions import ConcurrencyLimitExceeded, ModelHTTPError

from library.application.audit.context import (
    flush_audit_context,
    init_audit_context,
    set_actor,
    set_causation_id,
    set_correlation_id,
    set_request_metadata,
    set_source,
)
from library.application.errors import ApplicationError, ApplicationErrorType
from library.domain.audit.action import AuditAction
from library.domain.audit.actor import AuditActor
from library.domain.audit.event import AuditSource
from library.domain.errors import DomainError, DomainErrorType
from library.domain.value_objects.users import OrganizationID, UserID
from library.infrastructure.audit.publisher import record_audit_best_effort
from library.infrastructure.audit.snapshot import flush_snapshot_context, init_snapshot_context
from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType
from library.infrastructure.sentry import normalize_error_message
from library.logs import SIMPLE_LOGGER_NAME, add_log_context, flush_log_context, init_log_context
from library.presentation.api.environment import ComponentType
from library.presentation.errors import PresentationError, PresentationErrorType

logger = logging.getLogger(SIMPLE_LOGGER_NAME)

AUDIT_SOURCE_BY_COMPONENT = {
    ComponentType.SERVER: AuditSource.REST,
    ComponentType.LISTENER: AuditSource.LISTENER,
    ComponentType.EXECUTOR: AuditSource.EXECUTOR,
    ComponentType.TRIGGER: AuditSource.SYSTEM,
    ComponentType.JOB: AuditSource.JOB,
}


class ErrorRetryLogic(BaseModel):
    error_type: InfrastructureErrorType | ApplicationErrorType | DomainErrorType
    retries: int
    retry_delay_seconds: int


ERROR_RETRY_LOGIC: list[ErrorRetryLogic] = [
    ErrorRetryLogic(
        error_type=ApplicationErrorType.TRANSACTION_CONFLICT,
        retries=5,
        retry_delay_seconds=1,
    ),
]
NO_LOG_PATHS = ["/health"]
SENTRY_4XX_ERRORS = [429]  # 4xx error codes that we want to capture with sentry


class ExceptionHandlingRoute(APIRoute):
    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        original_route_handler = super().get_route_handler()

        async def exception_handler(request: Request) -> Response:
            log_context_token = init_log_context()
            audit_context_token = init_audit_context()
            snapshot_context_token = init_snapshot_context()
            request.state.start_time = time.time()
            request_body = await request.body()
            organization_id = self.__get_organization_id(request=request, body=request_body)
            user_id = self.__get_user_id(request=request)
            if user_id is not None:
                add_log_context(user_id=user_id)
            service = os.getenv("SERVICE", "")
            component_type = ComponentType(os.getenv("COMPONENT_TYPE", ""))
            component_name = os.getenv("COMPONENT_NAME") or self.name

            self.__init_audit_request_context(request=request, body=request_body, component_type=component_type)

            retry_count = 0
            while True:
                try:
                    parsed_body = json.loads(request_body.decode())
                    loggable_request_body = json.dumps(parsed_body)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    try:
                        loggable_request_body = request_body.decode("utf-8", errors="replace")
                    except Exception:
                        loggable_request_body = str(request_body)

                header_size = sum(len(f"{k}: {v}") for k, v in request.headers.items())
                request_size = len(request_body) + header_size

                http_request: dict[str, Any] = {
                    "requestMethod": request.method,
                    "requestUrl": str(request.url),
                    "requestSize": str(request_size),
                    "userAgent": request.headers.get("User-Agent", ""),
                    "remoteIp": request.client.host if request.client else "",
                    "referer": request.headers.get("Referer", ""),
                    "protocol": request.url.scheme.upper(),
                }

                try:
                    response = await original_route_handler(request)

                    is_redirect = 299 < response.status_code < 400
                    is_nolog_path = any(request.url.path.endswith(path) for path in NO_LOG_PATHS)

                    if not is_redirect and not is_nolog_path:
                        response_size = len(response.body)
                        latency_seconds = time.time() - request.state.start_time
                        http_request["status"] = response.status_code
                        http_request["responseSize"] = response_size
                        http_request["latency"] = f"{latency_seconds:.3f}s"

                        log = {
                            "logType": "custom",
                            "severity": "INFO",
                            "service": service,
                            "component_type": component_type,
                            "component_name": component_name,
                            "organization_id": organization_id,
                            "request_body": loggable_request_body,
                            "httpRequest": http_request,
                            "context": flush_log_context(token=log_context_token),
                        }
                        logger.info(json.dumps(log, default=str))
                    else:
                        flush_log_context(token=log_context_token)

                    flush_audit_context(token=audit_context_token)
                    flush_snapshot_context(token=snapshot_context_token)
                    return response
                except Exception as error:
                    if isinstance(error, InfrastructureError | ApplicationError | DomainError):
                        retry_logic = next(
                            (logic for logic in ERROR_RETRY_LOGIC if logic.error_type == error.error_type), None
                        )
                        if retry_logic and retry_count < retry_logic.retries:
                            retry_delay_seconds = retry_logic.retry_delay_seconds + random.random() * 0.5
                            logger.warning(
                                f"Retrying {error.error_type} after {retry_delay_seconds:.2f} seconds. "
                                f"Retry count: {retry_count + 1}/{retry_logic.retries}"
                            )
                            retry_count += 1
                            await asyncio.sleep(retry_delay_seconds)
                            continue

                    status_code, public_message, private_message = self.__process_exception(error)

                    latency_seconds = time.time() - request.state.start_time
                    http_request["status"] = status_code
                    http_request["latency"] = f"{latency_seconds:.3f}s"

                    log_severity = "ERROR"
                    log = {
                        "logType": "custom",
                        "httpRequest": http_request,
                        "severity": log_severity,
                        "service": service,
                        "component_type": component_type,
                        "component_name": component_name,
                        "organization_id": organization_id,
                        "status_code": status_code,
                        "message": private_message,
                        "request_body": loggable_request_body,
                        "context": flush_log_context(token=log_context_token),
                    }

                    is_redirect = 299 < status_code < 400
                    is_nolog_path = any(request.url.path.endswith(path) for path in NO_LOG_PATHS)
                    capture_with_sentry = (  # do not capture user errors
                        status_code >= 500 or status_code in SENTRY_4XX_ERRORS
                    ) and not self.__is_quota_state(error)

                    if not is_redirect and not is_nolog_path:
                        logger.error(json.dumps(log, default=str))

                        if capture_with_sentry:
                            with sentry_sdk.push_scope() as scope:
                                error_type = (
                                    error.error_type
                                    if isinstance(error, InfrastructureError | ApplicationError | DomainError)
                                    else "Exception"
                                )
                                scope.set_context(
                                    "error_details",
                                    {
                                        "error_type": error_type,
                                        "private_message": private_message,
                                        "public_message": public_message,
                                    },
                                )
                                scope.set_context("log", log)
                                scope.set_tag("status_code", status_code)
                                scope.set_tag("service", service)
                                scope.set_tag("component_type", component_type)
                                scope.set_tag("component_name", component_name)
                                scope.set_tag("organization_id", organization_id)

                                if isinstance(error, InfrastructureError | ApplicationError | DomainError):
                                    scope.fingerprint = [error.error_type, normalize_error_message(private_message)]
                                sentry_sdk.capture_exception(error)

                    if status_code == 403:
                        await self.__record_auth_denied(request=request, organization_id=organization_id)

                    flush_audit_context(token=audit_context_token)
                    flush_snapshot_context(token=snapshot_context_token)
                    raise HTTPException(status_code=status_code, detail=public_message)

        return exception_handler

    async def __record_auth_denied(self, *, request: Request, organization_id: OrganizationID | None) -> None:
        await record_audit_best_effort(
            action=AuditAction.AUTH_DENIED,
            resource_type="Endpoint",
            resource_id=request.url.path,
            organization_id=organization_id,
            changes=None,
        )

    def __init_audit_request_context(self, *, request: Request, body: bytes, component_type: ComponentType) -> None:
        source = AUDIT_SOURCE_BY_COMPONENT.get(component_type)
        if source is not None:
            set_source(source)

        trace_header = request.headers.get("X-Cloud-Trace-Context", "")
        trace_id = trace_header.split("/")[0] or None
        if trace_id is not None:
            set_correlation_id(trace_id)

        set_request_metadata(
            request_id=trace_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent") or None,
        )

        match component_type:
            case ComponentType.EXECUTOR:
                self.__restore_audit_actor(
                    raw_actor=request.headers.get("x-audit-actor"),
                    correlation_id=request.headers.get("x-audit-correlation-id"),
                    causation_id=request.headers.get("x-audit-causation-id"),
                )
            case ComponentType.LISTENER:
                attributes = self.__listener_attributes(body=body)
                self.__restore_audit_actor(
                    raw_actor=attributes.get("actor"),
                    correlation_id=attributes.get("correlation_id"),
                    causation_id=attributes.get("causation_id"),
                )
            case _:
                pass

    def __restore_audit_actor(
        self, *, raw_actor: str | None, correlation_id: str | None, causation_id: str | None
    ) -> None:
        if raw_actor:
            try:
                set_actor(AuditActor.model_validate_json(raw_actor))
            except ValueError:
                pass
        if correlation_id:
            set_correlation_id(correlation_id)
        if causation_id:
            set_causation_id(causation_id)

    def __listener_attributes(self, *, body: bytes) -> dict[str, str]:
        try:
            return json.loads(body).get("message", {}).get("attributes", {})
        except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
            return {}

    def __get_organization_id(self, *, request: Request, body: bytes) -> OrganizationID | None:
        component_type = ComponentType(os.getenv("COMPONENT_TYPE", ""))
        match component_type:
            case ComponentType.SERVER:
                authorization_header = request.headers.get("Authorization")
                if authorization_header:
                    try:
                        token = authorization_header.split(" ")[1]
                        decoded_token = jwt.decode(token, options={"verify_signature": False})
                        return OrganizationID(decoded_token.get("organization_id") or decoded_token["org_id"])
                    except Exception:
                        return None
                return None
            case ComponentType.LISTENER:
                raw_organization_id = json.loads(body).get("message", {}).get("attributes", {}).get("organization_id")
                if raw_organization_id:
                    return OrganizationID(raw_organization_id)
                return None
            case ComponentType.EXECUTOR:
                raw_organization_id = request.headers.get("x-organization-id")
                if raw_organization_id:
                    return OrganizationID(raw_organization_id)
                return None
            case ComponentType.TRIGGER:
                return None  # triggers don't have an organization_id
            case ComponentType.JOB:
                return None  # jobs don't have an organization_id

    def __get_user_id(self, *, request: Request) -> UserID | None:
        component_type = ComponentType(os.getenv("COMPONENT_TYPE", ""))
        if component_type is not ComponentType.SERVER:
            return None

        authorization_header = request.headers.get("Authorization")
        if not authorization_header:
            return None

        try:
            token = authorization_header.split(" ")[1]
            decoded_token = jwt.decode(token, options={"verify_signature": False})
            subject = decoded_token.get("sub")
            return UserID(subject) if subject else None
        except Exception:
            return None

    def __is_quota_state(self, exception: Exception) -> bool:
        if isinstance(exception, DomainError):
            return exception.error_type == DomainErrorType.QUOTA_ERROR
        if isinstance(exception, PresentationError):
            return exception.error_type == PresentationErrorType.QUOTA_ERROR
        return False

    def __process_exception(self, exception: Exception) -> tuple[int, str, str]:
        status_code = 500
        public_message = "Internal server error"
        private_message = str(exception)

        if isinstance(exception, ApplicationError):
            match exception.error_type:
                case ApplicationErrorType.VALIDATION_ERROR:
                    status_code = 400
                case ApplicationErrorType.PROCESS_FAILED:
                    status_code = 500
                case ApplicationErrorType.RESOURCE_NOT_FOUND:
                    status_code = 404
                case ApplicationErrorType.TRANSACTION_CONFLICT:
                    status_code = 500
            public_message = exception.public_message
            private_message = exception.private_message

        elif isinstance(exception, PresentationError):
            match exception.error_type:
                case PresentationErrorType.AUTHENTICATION_ERROR:
                    status_code = 401
                case PresentationErrorType.AUTHORIZATION_ERROR:
                    status_code = 403
                case PresentationErrorType.QUOTA_ERROR:
                    status_code = 429
            public_message = exception.public_message
            private_message = exception.private_message

        elif isinstance(exception, InfrastructureError):
            match exception.error_type:
                case InfrastructureErrorType.QUERY_ERROR:
                    status_code = 400
                case InfrastructureErrorType.VALIDATION_ERROR:
                    status_code = 400
                case InfrastructureErrorType.NOT_FOUND_ERROR:
                    status_code = 404
                case InfrastructureErrorType.CLOUD_ERROR:
                    status_code = 500
                case InfrastructureErrorType.OAUTH_ERROR:
                    status_code = 500
                case InfrastructureErrorType.VECTOR_INDEX_ERROR:
                    status_code = 500
                case InfrastructureErrorType.INELIGIBLE_EVENT:
                    status_code = 500
                case InfrastructureErrorType.INELIGIBLE_COMMAND:
                    status_code = 500
                case InfrastructureErrorType.INTEGRATION_ERROR:
                    status_code = 500
                case InfrastructureErrorType.INTEGRATION_AUTH_ERROR:
                    status_code = 403
                case InfrastructureErrorType.ENVIRONMENT_ERROR:
                    status_code = 500
                case InfrastructureErrorType.TRANSACTION_CONFLICT:
                    status_code = 500
            public_message = exception.public_message
            private_message = exception.private_message

        elif isinstance(exception, DomainError):
            match exception.error_type:
                case DomainErrorType.VALIDATION_ERROR:
                    status_code = 400
                case DomainErrorType.QUOTA_ERROR:
                    status_code = 429
            public_message = exception.public_message
            private_message = exception.private_message

        elif isinstance(exception, ModelHTTPError):
            status_code = exception.status_code
            public_message = "Upstream model provider error. Please try again."
            private_message = str(exception)

        elif isinstance(exception, ConcurrencyLimitExceeded):
            status_code = 503
            public_message = "Service temporarily overloaded. Please try again."
            private_message = str(exception)

        elif isinstance(exception, RequestValidationError):
            status_code = 422
            validation_errors = json.dumps(exception.errors(), default=str)
            public_message = "Error in request format. Please check your request and try again."
            private_message = validation_errors

        elif isinstance(exception, HTTPException):
            status_code = exception.status_code
            public_message = str(exception.detail)
            private_message = str(getattr(exception, "private_message", exception.detail))

        else:
            status_code = 500
            public_message = "Internal server error"
            private_message = traceback.format_exc()

        return status_code, public_message, private_message
