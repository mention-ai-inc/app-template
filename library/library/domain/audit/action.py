from library.domain.value_objects.core import EnumValueObject


class AuditAction(EnumValueObject):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    MEMBER_INVITED = "member.invited"
    MEMBER_REMOVED = "member.removed"
    MEMBER_ROLE_CHANGED = "member.role_changed"
    IMPERSONATION_STARTED = "impersonation.started"
    IMPERSONATION_ENDED = "impersonation.ended"
    INTEGRATION_CONNECTED = "integration.connected"
    INTEGRATION_DISCONNECTED = "integration.disconnected"
    AUTH_DENIED = "auth.denied"
    ADMIN_OPERATION_REQUESTED = "admin_operation.requested"
    ADMIN_OPERATION_COMPLETED = "admin_operation.completed"
