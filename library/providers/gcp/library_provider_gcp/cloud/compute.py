from pydantic import BaseModel, Field

from library_provider_gcp.cloud.base import AuthenticatedClient, raise_for_status


class BackendService(BaseModel):
    id: str
    name: str


class InstanceAccessConfig(BaseModel):
    nat_ip: str | None = Field(default=None, validation_alias="natIP")


class InstanceNetworkInterface(BaseModel):
    network_ip: str | None = Field(default=None, validation_alias="networkIP")
    access_configs: list[InstanceAccessConfig] = Field(default_factory=list, validation_alias="accessConfigs")


class Instance(BaseModel):
    name: str
    network_interfaces: list[InstanceNetworkInterface] = Field(
        default_factory=list, validation_alias="networkInterfaces"
    )

    @property
    def internal_ip(self) -> str | None:
        return self.network_interfaces[0].network_ip if self.network_interfaces else None

    @property
    def public_ip(self) -> str | None:
        if not self.network_interfaces:
            return None
        access_configs = self.network_interfaces[0].access_configs
        return access_configs[0].nat_ip if access_configs else None


class Compute:
    BASE_URL = "https://compute.googleapis.com/compute/v1"

    def __init__(self, *, token: str | None = None) -> None:
        self.token = token
        self._client: AuthenticatedClient | None = None

    @property
    def client(self) -> AuthenticatedClient:
        if self._client is None:
            self._client = AuthenticatedClient(base_url=Compute.BASE_URL, token=self.token)
        return self._client

    async def get_backend_service(self, *, project: str, name: str) -> BackendService:
        response = await self.client.get(f"/projects/{project}/global/backendServices/{name}")
        raise_for_status(response)
        return BackendService.model_validate(response.json())

    async def find_instance(self, *, project: str, name: str) -> Instance | None:
        response = await self.client.get(
            f"/projects/{project}/aggregated/instances", params={"filter": f'name="{name}"'}
        )
        raise_for_status(response)
        for scope in response.json().get("items", {}).values():
            for instance_data in scope.get("instances", []) or []:
                return Instance.model_validate(instance_data)
        return None
