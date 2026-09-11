from typing import ClassVar

from library.domain.commands.base import CommandPayload
from library.domain.value_objects.common import Service
from library.domain.value_objects.notes import NoteID
from library.domain.value_objects.users import OrganizationID


class SummarizeNote(CommandPayload):
    SERVICE: ClassVar[Service] = Service.NOTES

    organization_id: OrganizationID
    note_id: NoteID
