from typing import ClassVar

from control_plane.domain.value_objects.common import Service
from control_plane.domain.value_objects.users import OrganizationID
from library.domain.commands.base import CommandPayload
from library.domain.value_objects.notes import NoteID


class SummarizeNote(CommandPayload):
    SERVICE: ClassVar[Service] = Service.NOTES

    organization_id: OrganizationID
    note_id: NoteID
