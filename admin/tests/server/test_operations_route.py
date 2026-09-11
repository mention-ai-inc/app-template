from collections.abc import Callable
from typing import Any

import pytest


async def test_operations_reports_environment_and_image(
    monkeypatch: pytest.MonkeyPatch, client_factory: Callable[..., Any]
) -> None:
    monkeypatch.setenv("COMMIT_SHA", "abc123")
    monkeypatch.setenv("IMAGE_DIGEST", "sha256:test")

    async with client_factory() as client:
        response = await client.get("/operations")

    assert response.status_code == 200
    body = response.json()
    assert body["environment"] == "test"
    assert body["commit_sha"] == "abc123"
    assert body["image_digest"] == "sha256:test"
    assert "GET /organizations" in body["operations"]
    assert "POST /backfills/{name}/runs" in body["operations"]
    assert "POST /seed/runs" in body["operations"]
    assert "GET /health" not in body["operations"]


async def test_operations_reports_production_environment(client_factory: Callable[..., Any]) -> None:
    async with client_factory(environment="") as client:
        response = await client.get("/operations")

    assert response.status_code == 200
    assert response.json()["environment"] == "production"
