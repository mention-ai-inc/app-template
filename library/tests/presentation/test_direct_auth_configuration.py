import importlib
from unittest.mock import MagicMock, patch

import httpx
import pytest

from library.presentation.auth import direct
from library.presentation.errors import PresentationError


async def test_missing_jwks_configuration_fails_without_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLERK_JWKS_URL", raising=False)
    importlib.reload(direct)
    with patch.object(direct.httpx, "get") as request:
        with pytest.raises(PresentationError, match="CLERK_JWKS_URL"):
            await direct.get_user_from_token("invalid-token", users_client=MagicMock(), cache=MagicMock())
        request.assert_not_called()


@pytest.mark.parametrize("environment", ["feature", "production"])
async def test_jwks_configuration_is_explicit_per_environment(
    environment: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = f"https://{environment}.example.org/.well-known/jwks.json"
    monkeypatch.setenv("CLERK_JWKS_URL", url)
    importlib.reload(direct)
    response = httpx.Response(503, request=httpx.Request("GET", url))
    with patch.object(direct.httpx, "get", return_value=response) as request:
        with pytest.raises(PresentationError):
            await direct.get_user_from_token("invalid-token", users_client=MagicMock(), cache=MagicMock())
        request.assert_called_once_with(url, timeout=10)


async def test_failed_jwks_response_is_not_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    url = "https://feature.example.org/.well-known/jwks.json"
    monkeypatch.setenv("CLERK_JWKS_URL", url)
    importlib.reload(direct)
    response = httpx.Response(503, request=httpx.Request("GET", url))
    with patch.object(direct.httpx, "get", return_value=response) as request:
        for attempt in range(2):
            with pytest.raises(PresentationError):
                await direct.get_user_from_token("invalid-token", users_client=MagicMock(), cache=MagicMock())
            assert request.call_count == attempt + 1
