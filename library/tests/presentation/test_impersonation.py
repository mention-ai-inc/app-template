import datetime

import jwt
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from fastapi.security import HTTPAuthorizationCredentials
from pytest_mock import MockerFixture

from library.presentation.auth.impersonation import get_impersonated_user
from library.presentation.errors import PresentationError

KEY_ID = "the-only-key"
IDENTITY = "notes-s@acme-feature-0000.iam.gserviceaccount.com"


@pytest.fixture(scope="module")
def signing_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _certificate_pem(signing_key: rsa.RSAPrivateKey) -> str:
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, IDENTITY)])
    now = datetime.datetime.now(datetime.UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(signing_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=1))
        .sign(signing_key, hashes.SHA256())
    )
    return certificate.public_bytes(serialization.Encoding.PEM).decode()


def _public_key_pem(signing_key: rsa.RSAPrivateKey) -> str:
    return (
        signing_key.public_key()
        .public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )


def _token(signing_key: rsa.RSAPrivateKey) -> HTTPAuthorizationCredentials:
    credentials = jwt.encode(
        {
            "iss": IDENTITY,
            "uid": "user_1",
            "organization_id": "org_1",
            "clerk_role": "org:admin",
            "impersonating_service": "notes",
            "organization_public_metadata": {"": {}},
        },
        signing_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode(),
        algorithm="RS256",
        headers={"kid": KEY_ID},
    )
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=credentials)


def _identity_returning(mocker: MockerFixture, verifying_key: str) -> None:
    identity = mocker.AsyncMock()
    identity.verifying_keys.return_value = {KEY_ID: verifying_key}
    provider = mocker.patch("library.presentation.auth.impersonation.get_cloud_provider")
    provider.return_value.identity.return_value = identity


async def test_a_certificate_verifies_the_token(signing_key: rsa.RSAPrivateKey, mocker: MockerFixture) -> None:
    _identity_returning(mocker, _certificate_pem(signing_key))

    user = await get_impersonated_user(token=_token(signing_key))

    assert user.uid == "user_1"


async def test_a_bare_public_key_verifies_the_token(signing_key: rsa.RSAPrivateKey, mocker: MockerFixture) -> None:
    _identity_returning(mocker, _public_key_pem(signing_key))

    user = await get_impersonated_user(token=_token(signing_key))

    assert user.uid == "user_1"


async def test_a_key_that_did_not_sign_the_token_is_refused(
    signing_key: rsa.RSAPrivateKey, mocker: MockerFixture
) -> None:
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    _identity_returning(mocker, _public_key_pem(other_key))

    with pytest.raises(PresentationError):
        await get_impersonated_user(token=_token(signing_key))
