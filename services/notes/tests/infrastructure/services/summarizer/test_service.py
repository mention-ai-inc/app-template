from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from pytest_mock import MockerFixture

from library._testutils.llm import passthrough_run_llm
from library.domain.value_objects.users import OrganizationID
from notes_service.domain.aggregates.note.value_objects import NoteBody, NoteSummary, NoteTitle
from notes_service.infrastructure.services.summarizer.models import GeneratedSummary
from notes_service.infrastructure.services.summarizer.service import Summarizer


async def test_summarize_returns_llm_output(mocker: MockerFixture) -> None:
    __patch_agent(mocker, output=GeneratedSummary(summary=NoteSummary("Ship on Tuesday.")))

    summary = await Summarizer().summarize(organization_id=__org(), title=__title(), body=__body())

    assert summary == NoteSummary("Ship on Tuesday.")


async def test_summarize_strips_whitespace_from_llm_output(mocker: MockerFixture) -> None:
    __patch_agent(mocker, output=GeneratedSummary(summary=NoteSummary("  Ship on Tuesday.  ")))

    summary = await Summarizer().summarize(organization_id=__org(), title=__title(), body=__body())

    assert summary == NoteSummary("Ship on Tuesday.")


async def test_summarize_prompt_includes_title_and_body(mocker: MockerFixture) -> None:
    run_mock = __patch_agent(mocker, output=GeneratedSummary(summary=NoteSummary("Summary")))

    await Summarizer().summarize(organization_id=__org(), title=__title(), body=__body())

    user_prompt = run_mock.await_args_list[0].kwargs["user_prompt"]
    assert "Release plan" in user_prompt
    assert "Ship on Tuesday after the QA pass." in user_prompt


async def test_summarize_wraps_call_in_run_llm_with_telemetry(mocker: MockerFixture) -> None:
    run_llm_mock = __patch_agent(
        mocker, output=GeneratedSummary(summary=NoteSummary("Summary")), return_run_llm_mock=True
    )

    await Summarizer().summarize(organization_id=__org(), title=__title(), body=__body())

    run_llm_call = run_llm_mock.call_args
    telemetry = run_llm_call.kwargs["telemetry"]
    assert run_llm_call.kwargs["model"] == Summarizer.MODEL
    assert run_llm_call.kwargs["temperature"] == Summarizer.TEMPERATURE
    assert telemetry.span_name == ["note_summarizer", "summarize"]
    assert telemetry.organization_id == __org()


def __org() -> OrganizationID:
    return OrganizationID("org_test")


def __title() -> NoteTitle:
    return NoteTitle("Release plan")


def __body() -> NoteBody:
    return NoteBody("Ship on Tuesday after the QA pass.")


def __patch_agent(
    mocker: MockerFixture,
    *,
    output: GeneratedSummary,
    return_run_llm_mock: bool = False,
) -> AsyncMock | MagicMock:
    run_mock = AsyncMock(return_value=SimpleNamespace(output=output))
    agent = MagicMock()
    agent.run = run_mock
    mocker.patch("notes_service.infrastructure.services.summarizer.service.Agent", return_value=agent)
    run_llm_mock = mocker.patch(
        "notes_service.infrastructure.services.summarizer.service.run_llm",
        side_effect=passthrough_run_llm,
    )
    return run_llm_mock if return_run_llm_mock else run_mock
