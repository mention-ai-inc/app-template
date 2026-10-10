from pydantic import BaseModel, Field, field_validator

from notes_service.domain.aggregates.note.value_objects import NoteSummary


class GeneratedSummary(BaseModel):
    summary: NoteSummary = Field(
        description=(
            "A summary of the note in one to three plain sentences, written for someone who has not read it. "
            "State what the note says, not that it is a note. No headings, no bullet points, no quotation marks."
        )
    )

    @field_validator("summary", mode="after")
    def strip_summary(cls, v: NoteSummary) -> NoteSummary:
        return NoteSummary(v.strip())
