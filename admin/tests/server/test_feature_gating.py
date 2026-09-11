from collections.abc import Callable
from typing import Any

from fastapi import FastAPI

SEED_PATHS = [("POST", "/seed/runs")]


async def test_production_app_has_no_seed_routes(
    build_app: Callable[..., FastAPI], client_factory: Callable[..., Any]
) -> None:
    app = build_app(environment="")
    paths = app.openapi()["paths"]
    for _, path in SEED_PATHS:
        assert path not in paths

    async with client_factory(environment="") as client:
        for method, path in SEED_PATHS:
            response = await client.request(method, path, json={})
            assert response.status_code == 404, f"{method} {path} returned {response.status_code}"


async def test_feature_app_has_seed_routes(build_app: Callable[..., FastAPI]) -> None:
    app = build_app(environment="test")
    paths = app.openapi()["paths"]
    for _, path in SEED_PATHS:
        assert path in paths
