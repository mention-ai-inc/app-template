from collections.abc import AsyncGenerator, Mapping
from contextlib import asynccontextmanager
from typing import Any

from library.application.ports.users import IUsersClient
from library.domain.audit.action import AuditAction
from library.domain.audit.change import FieldChange
from library.domain.value_objects.users import OrganizationID
from library.infrastructure.audit.publisher import AuditEventPublisher

ADMIN_OPERATION_RESOURCE_TYPE = "AdminOperation"


class AdminAuditor:
    def __init__(self, *, publisher: AuditEventPublisher) -> None:
        self._publisher = publisher

    @asynccontextmanager
    async def operation(
        self,
        *,
        operation: str,
        organization_id: OrganizationID | None,
        parameters: Mapping[str, Any],
    ) -> AsyncGenerator[None]:
        await self.operation_requested(operation=operation, organization_id=organization_id, parameters=parameters)
        yield
        await self.operation_completed(operation=operation, organization_id=organization_id, parameters=parameters)

    async def launch_requested(
        self,
        *,
        operation: str,
        organization_id: str | None,
        parameters: Mapping[str, Any],
        users_client: IUsersClient,
    ) -> None:
        if organization_id is not None:
            await self.operation_requested(
                operation=operation, organization_id=OrganizationID(organization_id), parameters=parameters
            )
            return
        for organization in await users_client.list_organizations():
            await self.operation_requested(operation=operation, organization_id=organization.id, parameters=parameters)

    async def operation_requested(
        self,
        *,
        operation: str,
        organization_id: OrganizationID | None,
        parameters: Mapping[str, Any],
    ) -> None:
        await self.__publish(
            action=AuditAction.ADMIN_OPERATION_REQUESTED,
            operation=operation,
            organization_id=organization_id,
            parameters=parameters,
        )

    async def operation_completed(
        self,
        *,
        operation: str,
        organization_id: OrganizationID | None,
        parameters: Mapping[str, Any],
    ) -> None:
        await self.__publish(
            action=AuditAction.ADMIN_OPERATION_COMPLETED,
            operation=operation,
            organization_id=organization_id,
            parameters=parameters,
        )

    async def __publish(
        self,
        *,
        action: AuditAction,
        operation: str,
        organization_id: OrganizationID | None,
        parameters: Mapping[str, Any],
    ) -> None:
        changes = [
            FieldChange(field=field, before=None, after=value, value_captured=True)
            for field, value in parameters.items()
            if value is not None
        ]
        await self._publisher.quick_save(
            action=action,
            resource_type=ADMIN_OPERATION_RESOURCE_TYPE,
            resource_id=operation,
            organization_id=organization_id,
            changes=changes or None,
        )
