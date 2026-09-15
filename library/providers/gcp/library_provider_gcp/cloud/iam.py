import base64
import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from library_provider_gcp.cloud.base import AuthenticatedClient, raise_for_status


class AccessToken(BaseModel):
    access_token: str = Field(..., validation_alias="accessToken")
    expire_time: datetime = Field(..., validation_alias="expireTime")


class SignedBlob(BaseModel):
    key_id: str = Field(..., validation_alias="keyId")
    signed_blob: bytes = Field(..., validation_alias="signedBlob")


class SignedJWT(BaseModel):
    key_id: str = Field(..., validation_alias="keyId")
    signed_jwt: str = Field(..., validation_alias="signedJwt")


class IAM:
    BASE_URL = "https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts"

    def __init__(self, *, token: str | None = None) -> None:
        self.token = token
        self._client: AuthenticatedClient | None = None

    @property
    def client(self) -> AuthenticatedClient:
        if self._client is None:
            self._client = AuthenticatedClient(base_url=IAM.BASE_URL, token=self.token)
        return self._client

    async def generate_access_token(
        self, *, service_account_email: str, scopes: list[str] = ["https://www.googleapis.com/auth/cloud-platform"]
    ) -> AccessToken:
        response = await self.client.post(
            f"/{service_account_email}:generateAccessToken", json={"delegates": [], "scope": scopes}
        )
        raise_for_status(response)
        response_body = response.json()
        return AccessToken.model_validate(response_body)

    async def generate_id_token(self, *, service_account_email: str, audience: str) -> str:
        response = await self.client.post(
            f"/{service_account_email}:generateIdToken",
            json={"audience": audience, "include_email": True, "delegates": []},
        )
        raise_for_status(response)
        response_body = response.json()
        return response_body["token"]

    async def sign_blob(self, *, service_account_email: str, blob: bytes) -> SignedBlob:
        response = await self.client.post(
            f"/{service_account_email}:signBlob", json={"payload": base64.b64encode(blob).decode(), "delegates": []}
        )
        raise_for_status(response)
        response_body = response.json()
        return SignedBlob.model_validate(response_body)

    async def sign_jwt(self, *, service_account_email: str, payload: dict[str, Any]) -> SignedJWT:
        response = await self.client.post(
            f"/{service_account_email}:signJwt", json={"payload": json.dumps(payload), "delegates": []}
        )
        raise_for_status(response)
        response_body = response.json()
        return SignedJWT.model_validate(response_body)
