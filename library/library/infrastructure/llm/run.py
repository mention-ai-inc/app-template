import asyncio
import logging
import random
from collections.abc import Awaitable, Callable

from pydantic_ai import AgentRunResult
from pydantic_ai.exceptions import ModelHTTPError

from library.domain.value_objects.llm import LLMModelName
from library.infrastructure.llm.telemetry import LLMTelemetry, llm_span
from library.logs import SIMPLE_LOGGER_NAME

logger = logging.getLogger(SIMPLE_LOGGER_NAME)

LLM_RETRY_ATTEMPTS = 4
LLM_RETRY_BASE_DELAY_SECONDS = 1.0
_TRANSIENT_LLM_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504, 529})
_TRUNCATED_FINISH_REASON = "length"


class LLMOutputTruncatedError(Exception):
    def __init__(self, *, service: str, operation: str, provider_finish_reason: str | None) -> None:
        self.service = service
        self.operation = operation
        self.provider_finish_reason = provider_finish_reason
        super().__init__(
            f"LLM output truncated on {service}.{operation} (provider finish_reason={provider_finish_reason})"
        )


async def run_llm[OutputT](
    *,
    agent_run: Callable[[], Awaitable[AgentRunResult[OutputT]]],
    telemetry: LLMTelemetry,
    model: LLMModelName,
    temperature: float | None,
) -> AgentRunResult[OutputT]:
    attempt = 0
    while True:
        try:
            with llm_span(telemetry=telemetry, model=model, temperature=temperature):
                result = await agent_run()
        except ModelHTTPError as error:
            attempt += 1
            if attempt >= LLM_RETRY_ATTEMPTS or error.status_code not in _TRANSIENT_LLM_STATUS_CODES:
                raise
            delay = LLM_RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1)) + random.uniform(0.0, 1.0)
            logger.warning(
                f"Transient LLM error ({error.status_code}) on {telemetry.service}.{telemetry.operation} "
                f"(attempt {attempt}/{LLM_RETRY_ATTEMPTS}); retrying in {delay:.1f}s: {error}"
            )
            await asyncio.sleep(delay)
            continue

        if result.response.finish_reason == _TRUNCATED_FINISH_REASON:
            provider_finish_reason = (result.response.provider_details or {}).get("finish_reason")
            logger.warning(
                f"LLM output truncated on {telemetry.service}.{telemetry.operation} "
                f"(provider finish_reason={provider_finish_reason})"
            )
            raise LLMOutputTruncatedError(
                service=telemetry.service,
                operation=telemetry.operation,
                provider_finish_reason=provider_finish_reason,
            )

        return result
