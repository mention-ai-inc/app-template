from typing import Annotated

from control_plane.domain.events.base import EventPayload
from control_plane.domain.value_objects.core import IDValueObject
from control_plane.domain.value_objects.users import OrganizationID
from library.domain.aggregates import Aggregate
from library.domain.audit.classification import AuditByValue, AuditExcluded
from library.domain.commands.base import CommandPayload


class WidgetID(IDValueObject):
    pass


class Widget(Aggregate[WidgetID, EventPayload, CommandPayload]):
    id: WidgetID
    organization_id: OrganizationID
    status: Annotated[str, AuditByValue]
    secret: Annotated[str, AuditExcluded]
    notes: str


def make_widget(*, status: str = "draft", secret: str = "s3cr3t", notes: str = "note") -> Widget:
    return Widget(
        id=WidgetID(),
        organization_id=OrganizationID("org_widget"),
        status=status,
        secret=secret,
        notes=notes,
    )
