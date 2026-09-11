from typing import NamedTuple

from library.domain.value_objects.users import OrganizationID
from notes_service.domain.aggregates.note.value_objects import NoteBody, NoteSummary, NoteTitle
from notes_service.domain.interfaces.summarizer import ISummarizer


class SummarizeCall(NamedTuple):
    organization_id: OrganizationID
    title: NoteTitle
    body: NoteBody


class FakeSummarizer(ISummarizer):
    def __init__(self, *, response: NoteSummary | None = None) -> None:
        self._response = response
        self.last_call: SummarizeCall | None = None
        self.call_count = 0

    async def summarize(self, *, organization_id: OrganizationID, title: NoteTitle, body: NoteBody) -> NoteSummary:
        self.last_call = SummarizeCall(organization_id=organization_id, title=title, body=body)
        self.call_count += 1
        return self._response or NoteSummary(body[:40])
