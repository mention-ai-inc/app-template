from library.domain.events.base import EventPayload
from library.domain.value_objects.notes import NoteID
from library.domain.value_objects.users import OrganizationID


class NoteCreated(EventPayload):
    organization_id: OrganizationID
    note_id: NoteID


class NoteSummarized(EventPayload):
    organization_id: OrganizationID
    note_id: NoteID
