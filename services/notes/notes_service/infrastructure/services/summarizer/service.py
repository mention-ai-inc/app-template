from pydantic_ai import Agent

from library.domain.value_objects.llm import LLMModelName
from library.domain.value_objects.users import OrganizationID
from library.infrastructure.llm.run import run_llm
from library.infrastructure.llm.settings import model_settings
from library.infrastructure.llm.telemetry import LLMTelemetry
from library.infrastructure.service import InfrastructureService
from notes_service.domain.aggregates.note.value_objects import NoteBody, NoteSummary, NoteTitle
from notes_service.domain.interfaces.summarizer import ISummarizer
from notes_service.infrastructure.services.summarizer.models import GeneratedSummary

SUMMARIZER_INSTRUCTIONS = (
    "You will be given a note written by a member of an organization: its title and its body. "
    "Summarize the note in one to three plain sentences so a colleague can tell what it is about "
    "without reading it. Keep the note's own terms. Do not add anything the note does not say."
)


class Summarizer(ISummarizer, InfrastructureService):
    MODEL = LLMModelName.GEMINI_35_FLASH_LITE
    TEMPERATURE = 0.0

    async def summarize(self, *, organization_id: OrganizationID, title: NoteTitle, body: NoteBody) -> NoteSummary:
        telemetry = LLMTelemetry(
            service="note_summarizer",
            operation="summarize",
            organization_id=organization_id,
            trace_id="",
        )
        agent = Agent(
            model=self.MODEL,
            output_type=GeneratedSummary,
            instructions=SUMMARIZER_INSTRUCTIONS,
            model_settings=model_settings(temperature=self.TEMPERATURE),
        )

        generation_result = await run_llm(
            telemetry=telemetry,
            model=self.MODEL,
            temperature=self.TEMPERATURE,
            agent_run=lambda: agent.run(user_prompt=self.__build_prompt(title=title, body=body)),
        )

        return generation_result.output.summary

    def __build_prompt(self, *, title: NoteTitle, body: NoteBody) -> str:
        return f"Title: {title}\n\n{body}"
