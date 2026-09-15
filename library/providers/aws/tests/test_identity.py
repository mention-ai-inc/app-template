import pytest
from library_provider_aws.identity import AwsRuntimeContext, KmsIdentity, reset_verifying_keys
from library_provider_aws.secrets import SecretsManager

SERVICE = "notes"
VERSION_UUID = "6a0f2b3c-4d5e-4f60-8a1b-2c3d4e5f6071"


class TestSigningKeys:
    @pytest.fixture
    def identity(self, moto_endpoint: str) -> KmsIdentity:  # noqa: ARG002
        reset_verifying_keys()
        return KmsIdentity()

    def test_the_signing_key_is_named_after_the_service_role(self, identity: KmsIdentity) -> None:
        service_identity = identity.service_identity(service=SERVICE)

        assert identity.signing_key_alias(identity=service_identity) == "alias/notes-s"

    async def test_a_verifying_key_comes_back_as_a_pem(self, identity: KmsIdentity) -> None:
        keys = await identity.verifying_keys(identity=identity.service_identity(service=SERVICE))

        assert all(value.startswith("-----BEGIN PUBLIC KEY-----") for value in keys.values())

    async def test_a_second_read_is_served_from_the_cache(self, identity: KmsIdentity) -> None:
        service_identity = identity.service_identity(service=SERVICE)
        first = await identity.verifying_keys(identity=service_identity)

        assert await identity.verifying_keys(identity=service_identity) is first

    async def test_a_refresh_goes_back_to_kms(self, identity: KmsIdentity) -> None:
        service_identity = identity.service_identity(service=SERVICE)
        first = await identity.verifying_keys(identity=service_identity)

        refreshed = await identity.verifying_keys(identity=service_identity, refresh=True)

        assert refreshed is not first
        assert refreshed == first


class TestRuntimeContext:
    def test_the_deployment_id_is_the_account(self, moto_endpoint: str) -> None:  # noqa: ARG002
        assert AwsRuntimeContext().get_deployment_id() == "123456789012"

    def test_scoping_prefixes_the_feature_environment_on_every_call(
        self,
        moto_endpoint: str,  # noqa: ARG002
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        runtime_context = AwsRuntimeContext()
        monkeypatch.setenv("FEATURE_ENVIRONMENT", "pr7")

        assert runtime_context.scope_resource_name("notes-commands") == "pr7notes-commands"


class TestSecretVersions:
    def test_latest_becomes_the_current_stage(self) -> None:
        assert SecretsManager().version_selector("latest") == {"VersionStage": "AWSCURRENT"}

    def test_a_uuid_becomes_a_version_id(self) -> None:
        assert SecretsManager().version_selector(VERSION_UUID) == {"VersionId": VERSION_UUID}

    def test_anything_else_becomes_a_version_stage(self) -> None:
        assert SecretsManager().version_selector("1") == {"VersionStage": "1"}
