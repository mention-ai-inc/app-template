from library.application.ports.secrets import ISecretStore

SECRET_ID = "conformance-secret"


async def test_accessing_a_secret_version_returns_a_string(secret_store: ISecretStore) -> None:
    secret = await secret_store.access_secret_version(secret_id=SECRET_ID)

    assert isinstance(secret, str)
    assert secret != ""


async def test_an_explicit_version_is_accepted(secret_store: ISecretStore) -> None:
    secret = await secret_store.access_secret_version(secret_id=SECRET_ID, version_id="1")

    assert isinstance(secret, str)
    assert secret != ""
