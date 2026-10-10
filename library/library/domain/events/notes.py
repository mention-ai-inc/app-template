from control_plane.domain.events.base import EventPayload
from control_plane.domain.value_objects.users import OrganizationID
from library.domain.value_objects.notes import NoteID


class NoteCreated(EventPayload):
    organization_id: OrganizationID
    note_id: NoteID


class NoteSummarized(EventPayload):
    organization_id: OrganizationID
    note_id: NoteID
