from typing import Protocol


class ISecretStore(Protocol):
    async def access_secret_version(self, *, secret_id: str, version_id: str = "latest") -> str: ...
