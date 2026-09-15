import base64

from pydantic import BaseModel, Field

from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType
from library_provider_gcp.cloud.base import AuthenticatedClient
from library_provider_gcp.cloud.constants import OPERATIONS_PROJECT_ID

SECRETS_PROJECT = OPERATIONS_PROJECT_ID


class Secret(BaseModel):
    name: str
    create_time: str = Field(..., validation_alias="createTime")
    update_time: str | None = Field(default=None, validation_alias="updateTime")
    labels: dict[str, str] | None = None


class SecretManager:
    BASE_URL = "https://secretmanager.googleapis.com/v1"

    def __init__(self, *, project: str = SECRETS_PROJECT, token: str | None = None, use_cache: bool = False) -> None:
        self.project = project
        self.token = token
        self._client: AuthenticatedClient | None = None
        self.use_cache = use_cache
        self._cache: dict[str, str] = {}

    @property
    def client(self) -> AuthenticatedClient:
        if self._client is None:
            self._client = AuthenticatedClient(base_url=SecretManager.BASE_URL, token=self.token)
        return self._client

    async def access_secret_version(self, *, secret_id: str, version_id: str = "latest") -> str:
        url = f"/projects/{self.project}/secrets/{secret_id}/versions/{version_id}:access"
        if self.use_cache:
            if secret_id in self._cache:
                return self._cache[secret_id]
            else:
                response = await self.client.get(url)
                if response.status_code != 200:
                    raise InfrastructureError(
                        error_type=InfrastructureErrorType.CLOUD_ERROR, message=f"Error accessing secret: {secret_id}"
                    )

                response_body = response.json()
                secret = base64.b64decode(response_body["payload"]["data"]).decode()
                self._cache[secret_id] = secret
                return secret
        else:
            response = await self.client.get(url)
            if response.status_code != 200:
                raise InfrastructureError(
                    error_type=InfrastructureErrorType.CLOUD_ERROR, message=f"Error accessing secret: {secret_id}"
                )

            response_body = response.json()
            return base64.b64decode(response_body["payload"]["data"]).decode()
