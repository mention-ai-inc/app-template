import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, cast

import google.auth
from google.auth.transport.requests import Request
from httpx import AsyncClient, HTTPError, HTTPStatusError, Response

from library.logs import SIMPLE_LOGGER_NAME

logger = logging.getLogger(SIMPLE_LOGGER_NAME)
CACHE_TTL = 60 * 60
DEFAULT_TIMEOUT = 30


def _override[**P, R](to_replace: Callable[P, R]) -> Callable[[Callable[..., Any]], Callable[..., R]]:  # noqa: ARG001
    def wrapper(replacement: Callable[..., R]) -> Callable[..., R]:
        return replacement

    return wrapper


def raise_for_status(response: Response) -> None:
    try:
        response.raise_for_status()
    except HTTPError as error:
        if isinstance(error, HTTPStatusError) and error.response.status_code == 404:
            raise
        else:
            logger.error(response.text)
            raise


class AuthenticatedClient(AsyncClient):
    shared_token = ""
    shared_token_last_updated = 0

    def __init__(self, *, base_url: str, token: str | None = None, timeout: int = DEFAULT_TIMEOUT) -> None:
        super().__init__(base_url=base_url, follow_redirects=True, timeout=timeout)
        self.token_override = token

    @classmethod
    def update_shared_token(cls) -> None:
        if cls.shared_token_last_updated + CACHE_TTL < datetime.now(UTC).timestamp():
            cls.shared_token = _get_access_token()
            cls.shared_token_last_updated = datetime.now(UTC).timestamp()

    @classmethod
    def clear_shared_token(cls) -> None:
        cls.shared_token = ""
        cls.shared_token_last_updated = 0

    @property
    def token(self) -> str:
        if self.token_override is not None:
            return self.token_override

        self.update_shared_token()
        return self.shared_token

    @_override(AsyncClient.get)
    async def get(self, path: str, **kwargs: Any) -> Response:
        self.__patch_headers(kwargs)
        initial_response = await super().get(path, **kwargs)

        if initial_response.status_code == 401:
            self.clear_shared_token()
            self.__patch_headers(kwargs)
            return await super().get(path, **kwargs)
        else:
            return initial_response

    @_override(AsyncClient.post)
    async def post(self, path: str, *, json: dict[str, Any] | None = None, **kwargs: Any) -> Response:
        self.__patch_headers(kwargs)
        initial_response = await super().post(path, json=json, **kwargs)

        if initial_response.status_code == 401:
            self.clear_shared_token()
            self.__patch_headers(kwargs)
            return await super().post(path, json=json, **kwargs)
        else:
            return initial_response

    @_override(AsyncClient.put)
    async def put(self, path: str, *, json: dict[str, Any] | None = None, **kwargs: Any) -> Response:
        self.__patch_headers(kwargs)
        initial_response = await super().put(path, json=json, **kwargs)

        if initial_response.status_code == 401:
            self.clear_shared_token()
            self.__patch_headers(kwargs)
            return await super().put(path, json=json, **kwargs)
        else:
            return initial_response

    @_override(AsyncClient.patch)
    async def patch(self, path: str, *, json: dict[str, Any] | None = None, **kwargs: Any) -> Response:
        self.__patch_headers(kwargs)
        initial_response = await super().patch(path, json=json, **kwargs)

        if initial_response.status_code == 401:
            self.clear_shared_token()
            self.__patch_headers(kwargs)
            return await super().patch(path, json=json, **kwargs)
        else:
            return initial_response

    @_override(AsyncClient.delete)
    async def delete(self, path: str, **kwargs: Any) -> Response:
        self.__patch_headers(kwargs)
        initial_response = await super().delete(path, **kwargs)

        if initial_response.status_code == 401:
            self.clear_shared_token()
            self.__patch_headers(kwargs)
            return await super().delete(path, **kwargs)
        else:
            return initial_response

    def __patch_headers(self, kwargs: dict[str, Any]) -> None:
        kwargs["headers"] = kwargs.get("headers", {})
        kwargs["headers"]["Authorization"] = f"Bearer {self.token}"


def _get_access_token() -> str:
    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    credentials = cast(Any, credentials)
    credentials.refresh(Request())

    if credentials.token is None:
        raise ValueError("No access token found.")

    return credentials.token
