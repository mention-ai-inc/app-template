import json
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

import logfire

from library.domain.value_objects.llm import LLMModelName
from library.domain.value_objects.users import OrganizationID


@dataclass(frozen=True)
class LLMTelemetry:
    service: str
    operation: str
    organization_id: OrganizationID
    trace_id: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def span_name(self) -> list[str]:
        return [self.service, self.operation]


@contextmanager
def llm_span(*, telemetry: LLMTelemetry, model: LLMModelName, temperature: float | None) -> Generator[None]:
    metadata = {
        **telemetry.metadata,
        "organization_id": str(telemetry.organization_id),
        "span_name": telemetry.span_name,
        "trace_id": telemetry.trace_id,
    }

    with logfire.span(f"llm.{telemetry.service}.{telemetry.operation}") as span:
        span.set_attribute("llm.service", telemetry.service)
        span.set_attribute("llm.operation", telemetry.operation)
        span.set_attribute("organization_id", str(telemetry.organization_id))
        span.set_attribute("llm.trace_id", telemetry.trace_id)
        span.set_attribute("llm.span_name", telemetry.span_name)
        span.set_attribute("llm.operation_path", ".".join(telemetry.span_name))
        span.set_attribute("llm.model", model)
        span.set_attribute("llm.temperature", temperature)
        span.set_attribute("llm.metadata_raw", json.dumps(metadata, default=str, sort_keys=True))
        yield
