import re

from library_provider_aws.clients import client, scope_resource_name

CURRENT_VERSION_STAGE = "AWSCURRENT"
LATEST_VERSION_ID = "latest"
VERSION_ID_PATTERN = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


class SecretsManager:
    async def access_secret_version(self, *, secret_id: str, version_id: str = "latest") -> str:
        request = {"SecretId": scope_resource_name(secret_id), **self.version_selector(version_id)}

        async with client("secretsmanager") as secretsmanager:
            response = await secretsmanager.get_secret_value(**request)

        secret_string = response.get("SecretString")
        if secret_string is not None:
            return str(secret_string)
        return bytes(response["SecretBinary"]).decode()

    def version_selector(self, version_id: str, /) -> dict[str, str]:
        if version_id == LATEST_VERSION_ID:
            return {"VersionStage": CURRENT_VERSION_STAGE}
        if VERSION_ID_PATTERN.match(version_id) is not None:
            return {"VersionId": version_id}
        return {"VersionStage": version_id}
