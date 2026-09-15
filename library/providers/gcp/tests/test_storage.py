from typing import Any

import pytest
from httpx import HTTPStatusError, Request, Response

import library_provider_gcp.cloud.storage as storage_module
from library_provider_gcp.cloud.base import AuthenticatedClient
from library_provider_gcp.cloud.storage import INSERT_RETRY_ATTEMPTS, Storage


async def test_insert_retries_a_rate_limited_write_until_it_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    statuses = [429, 429, 200]
    attempts: list[str] = []

    async def fake_post(self: AuthenticatedClient, url: str, **kwargs: Any) -> Response:  # noqa: ARG001
        attempts.append(url)
        return Response(statuses[len(attempts) - 1], request=Request("POST", url))

    monkeypatch.setattr(AuthenticatedClient, "post", fake_post)
    delays = __capture_sleep(monkeypatch)

    await Storage(token="token").insert(filepath="orgs/org_test/thing.json", content=b"{}", bucket="bucket")

    assert len(attempts) == 3
    assert len(delays) == 2
    assert delays[0] < delays[1]


async def test_insert_raises_when_every_attempt_is_rate_limited(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts: list[str] = []

    async def fake_post(self: AuthenticatedClient, url: str, **kwargs: Any) -> Response:  # noqa: ARG001
        attempts.append(url)
        return Response(429, request=Request("POST", url))

    monkeypatch.setattr(AuthenticatedClient, "post", fake_post)
    __capture_sleep(monkeypatch)

    with pytest.raises(HTTPStatusError) as error:
        await Storage(token="token").insert(filepath="orgs/org_test/thing.json", content=b"{}", bucket="bucket")

    assert error.value.response.status_code == 429
    assert len(attempts) == INSERT_RETRY_ATTEMPTS


async def test_insert_does_not_retry_other_client_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts: list[str] = []

    async def fake_post(self: AuthenticatedClient, url: str, **kwargs: Any) -> Response:  # noqa: ARG001
        attempts.append(url)
        return Response(403, request=Request("POST", url))

    monkeypatch.setattr(AuthenticatedClient, "post", fake_post)
    __capture_sleep(monkeypatch)

    with pytest.raises(HTTPStatusError) as error:
        await Storage(token="token").insert(filepath="orgs/org_test/thing.json", content=b"{}", bucket="bucket")

    assert error.value.response.status_code == 403
    assert len(attempts) == 1


def __capture_sleep(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    delays: list[float] = []

    async def fake_sleep(delay: float) -> None:
        delays.append(delay)

    monkeypatch.setattr(storage_module.asyncio, "sleep", fake_sleep)
    return delays
