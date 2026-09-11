from datetime import UTC, datetime, timedelta
from typing import ClassVar, Self

from library.domain.aggregates import Aggregate
from library.domain.commands.notes import SummarizeNote
from library.domain.errors import DomainError
from library.domain.events.notes import NoteCreated, NoteSummarized
from library.domain.value_objects.notes import NoteID
from library.domain.value_objects.users import OrganizationID, UserID
from notes_service.domain.aggregates.note.value_objects import NoteBody, NoteStatus, NoteSummary, NoteTitle

NoteEvent = NoteCreated | NoteSummarized
NoteCommand = SummarizeNote


class Note(Aggregate[NoteID, NoteEvent, NoteCommand]):
    author_id: UserID
    title: NoteTitle
    body: NoteBody
    status: NoteStatus
    summary: NoteSummary | None
    created_at: datetime

    RETENTION: ClassVar[timedelta] = timedelta(days=90)

    @classmethod
    def purge_cutoff(cls, *, as_of: datetime) -> datetime:
        return as_of - cls.RETENTION

    @classmethod
    def create(
        cls,
        *,
        organization_id: OrganizationID,
        author_id: UserID,
        title: NoteTitle,
        body: NoteBody,
    ) -> Self:
        if not title.strip():
            raise DomainError(message="A note must have a title", public_message="Give the note a title")
        if not body.strip():
            raise DomainError(message="A note must have a body", public_message="Write something in the note")

        note = cls(
            id=NoteID(),
            organization_id=organization_id,
            author_id=author_id,
            title=title,
            body=body,
            status=NoteStatus.PENDING,
            summary=None,
            created_at=datetime.now(UTC),
        )
        note.add_event(NoteCreated(organization_id=organization_id, note_id=note.id))
        return note

    def request_summary(self) -> None:
        if self.status != NoteStatus.PENDING:
            return

        self.status = NoteStatus.SUMMARIZING
        self.add_command(SummarizeNote(organization_id=self.organization_id, note_id=self.id))

    def record_summary(self, *, summary: NoteSummary) -> None:
        self.summary = summary
        self.status = NoteStatus.SUMMARIZED
        self.add_event(NoteSummarized(organization_id=self.organization_id, note_id=self.id))
