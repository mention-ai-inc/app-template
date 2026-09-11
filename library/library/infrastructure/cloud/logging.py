from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from library.infrastructure.cloud.base import AuthenticatedClient, raise_for_status


class LogEntry(BaseModel):
    timestamp: datetime
    severity: str | None = None
    text_payload: str | None = Field(default=None, validation_alias="textPayload")
    json_payload: dict[str, Any] | None = Field(default=None, validation_alias="jsonPayload")

    @property
    def message(self) -> str:
        if self.text_payload is not None:
            return self.text_payload
        if self.json_payload is not None:
            return str(self.json_payload.get("message", self.json_payload))
        return ""


class CloudLogging:
    BASE_URL = "https://logging.googleapis.com/v2"

    def __init__(self, *, token: str | None = None) -> None:
        self.token = token
        self._client: AuthenticatedClient | None = None

    @property
    def client(self) -> AuthenticatedClient:
        if self._client is None:
            self._client = AuthenticatedClient(base_url=CloudLogging.BASE_URL, token=self.token)
        return self._client

    async def list_entries(self, *, project: str, log_filter: str, page_size: int = 1000) -> list[LogEntry]:
        response = await self.client.post(
            "/entries:list",
            json={
                "resourceNames": [f"projects/{project}"],
                "filter": log_filter,
                "orderBy": "timestamp asc",
                "pageSize": page_size,
            },
        )
        raise_for_status(response)
        entries = response.json().get("entries", [])
        return [LogEntry.model_validate(entry) for entry in entries]
