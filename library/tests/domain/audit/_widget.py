from typing import Annotated

from library.domain.aggregates import Aggregate
from library.domain.audit.classification import AuditByValue, AuditExcluded
from library.domain.commands.base import CommandPayload
from library.domain.events.base import EventPayload
from library.domain.value_objects.core import IDValueObject
from library.domain.value_objects.users import OrganizationID


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
