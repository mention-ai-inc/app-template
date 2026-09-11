from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.usage import RunUsage
from pytest_mock import MockerFixture

import library.infrastructure.llm.run as run_module
from library.domain.value_objects.llm import LLMModelName
from library.domain.value_objects.users import OrganizationID
from library.infrastructure.llm.run import LLM_RETRY_ATTEMPTS, LLMOutputTruncatedError, run_llm
from library.infrastructure.llm.telemetry import LLMTelemetry


async def test_run_llm_returns_the_agent_run_result() -> None:
    sentinel = __agent_result()

    async def _agent_run() -> SimpleNamespace:
        return sentinel

    result = await run_llm(
        telemetry=__telemetry(),
        model=LLMModelName.GEMINI_36_FLASH,
        temperature=0.0,
        agent_run=_agent_run,  # pyright: ignore[reportArgumentType]
    )

    assert result is sentinel


async def test_run_llm_propagates_agent_run_errors() -> None:
    async def _agent_run() -> SimpleNamespace:
        raise RuntimeError("model failed")

    with pytest.raises(RuntimeError, match="model failed"):
        await run_llm(
            telemetry=__telemetry(),
            model=LLMModelName.GEMINI_36_FLASH,
            temperature=0.0,
            agent_run=_agent_run,  # pyright: ignore[reportArgumentType]
        )


async def test_run_llm_retries_transient_model_http_error_then_succeeds(mocker: MockerFixture) -> None:
    sleep_mock = __patch_sleep(mocker)
    sentinel = __agent_result()
    calls = {"count": 0}

    async def _agent_run() -> SimpleNamespace:
        calls["count"] += 1
        if calls["count"] == 1:
            raise ModelHTTPError(status_code=503, model_name="gemini-3.6-flash")
        return sentinel

    result = await run_llm(
        telemetry=__telemetry(),
        model=LLMModelName.GEMINI_36_FLASH,
        temperature=0.0,
        agent_run=_agent_run,  # pyright: ignore[reportArgumentType]
    )

    assert result is sentinel
    assert calls["count"] == 2
    assert sleep_mock.await_count == 1


async def test_run_llm_does_not_retry_non_transient_model_http_error(mocker: MockerFixture) -> None:
    sleep_mock = __patch_sleep(mocker)
    calls = {"count": 0}

    async def _agent_run() -> SimpleNamespace:
        calls["count"] += 1
        raise ModelHTTPError(status_code=400, model_name="gemini-3.6-flash")

    with pytest.raises(ModelHTTPError):
        await run_llm(
            telemetry=__telemetry(),
            model=LLMModelName.GEMINI_36_FLASH,
            temperature=0.0,
            agent_run=_agent_run,  # pyright: ignore[reportArgumentType]
        )

    assert calls["count"] == 1
    assert sleep_mock.await_count == 0


async def test_run_llm_raises_after_exhausting_retries(mocker: MockerFixture) -> None:
    sleep_mock = __patch_sleep(mocker)
    calls = {"count": 0}

    async def _agent_run() -> SimpleNamespace:
        calls["count"] += 1
        raise ModelHTTPError(status_code=503, model_name="gemini-3.6-flash")

    with pytest.raises(ModelHTTPError):
        await run_llm(
            telemetry=__telemetry(),
            model=LLMModelName.GEMINI_36_FLASH,
            temperature=0.0,
            agent_run=_agent_run,  # pyright: ignore[reportArgumentType]
        )

    assert calls["count"] == LLM_RETRY_ATTEMPTS
    assert sleep_mock.await_count == LLM_RETRY_ATTEMPTS - 1


async def test_run_llm_raises_when_output_truncated() -> None:
    truncated = __agent_result(finish_reason="length", provider_details={"finish_reason": "MAX_TOKENS"})

    async def _agent_run() -> SimpleNamespace:
        return truncated

    with pytest.raises(LLMOutputTruncatedError) as exc_info:
        await run_llm(
            telemetry=__telemetry(),
            model=LLMModelName.GEMINI_36_FLASH,
            temperature=0.0,
            agent_run=_agent_run,  # pyright: ignore[reportArgumentType]
        )

    assert exc_info.value.provider_finish_reason == "MAX_TOKENS"


def __telemetry() -> LLMTelemetry:
    return LLMTelemetry(
        service="summarizer",
        operation="summarize_note",
        organization_id=OrganizationID("org_test"),
        trace_id="trace-1",
    )


def __patch_sleep(mocker: MockerFixture) -> AsyncMock:
    return mocker.patch.object(run_module.asyncio, "sleep", new_callable=AsyncMock)


def __agent_result(
    *, finish_reason: str = "stop", provider_details: dict[str, object] | None = None
) -> SimpleNamespace:
    return SimpleNamespace(
        usage=RunUsage(input_tokens=10, output_tokens=20, details={}),
        response=SimpleNamespace(finish_reason=finish_reason, provider_details=provider_details),
    )
