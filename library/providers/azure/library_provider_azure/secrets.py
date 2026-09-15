from azure.core.exceptions import ResourceNotFoundError

from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType
from library_provider_azure.clients import AzureClients

LATEST_VERSION = "latest"


def to_key_vault_name(secret_id: str, /) -> str:
    return secret_id.replace("_", "-")


class KeyVaultSecretStore:
    async def access_secret_version(self, *, secret_id: str, version_id: str = LATEST_VERSION) -> str:
        version = None if version_id == LATEST_VERSION else version_id

        try:
            secret = await AzureClients.secrets().get_secret(to_key_vault_name(secret_id), version)
        except ResourceNotFoundError as error:
            raise InfrastructureError(
                error_type=InfrastructureErrorType.CLOUD_ERROR, message=f"Error accessing secret: {secret_id}"
            ) from error

        if secret.value is None:
            raise InfrastructureError(
                error_type=InfrastructureErrorType.CLOUD_ERROR, message=f"Secret {secret_id} has no value"
            )

        return secret.value
