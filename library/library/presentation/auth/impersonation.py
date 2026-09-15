import logging
import os

import jwt
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from library.infrastructure.users import ClerkRole
from library.logs import SIMPLE_LOGGER_NAME
from library.presentation.auth.types import AuthenticatedUser
from library.presentation.errors import PresentationError, PresentationErrorType
from library.providers.registry import get_cloud_provider

logger = logging.getLogger(SIMPLE_LOGGER_NAME)


def __load_public_key_from_x509(certificate: str) -> bytes:
    cert = x509.load_pem_x509_certificate(certificate.encode(), default_backend())
    public_key = cert.public_key()
    pem_public_key = public_key.public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return pem_public_key


async def generate_impersonation_token(*, calling_service: str, user_id: str, organization_id: str) -> str:
    identity = get_cloud_provider().identity()
    service_identity = identity.service_identity(service=calling_service)
    return await identity.sign_jwt(
        identity=service_identity,
        payload={
            "iss": service_identity,
            "uid": user_id,
            "organization_id": organization_id,
            "clerk_role": ClerkRole.ADMIN,
            "impersonating_service": calling_service,
            "organization_public_metadata": {os.getenv("FEATURE_ENVIRONMENT", ""): {}},
        },
    )


async def __verifying_keys_for(*, identity: str, key_id: str) -> dict[str, str]:
    identity_provider = get_cloud_provider().identity()
    public_keys = await identity_provider.verifying_keys(identity=identity)
    if key_id in public_keys:
        return public_keys
    return await identity_provider.verifying_keys(identity=identity, refresh=True)


async def get_impersonated_user(*, token: HTTPAuthorizationCredentials = Depends(HTTPBearer())) -> AuthenticatedUser:
    try:
        headers = jwt.get_unverified_header(token.credentials)
        unverified_token = jwt.decode(token.credentials, options={"verify_signature": False})

        public_keys = await __verifying_keys_for(identity=unverified_token["iss"], key_id=headers["kid"])
        public_key = __load_public_key_from_x509(public_keys[headers["kid"]])

        decoded_token = jwt.decode(token.credentials, public_key, algorithms=headers["alg"])
        user = AuthenticatedUser.model_validate({**decoded_token, "token": token.credentials})

        return user
    except Exception as error:
        raise PresentationError(
            error_type=PresentationErrorType.AUTHENTICATION_ERROR, message=str(error), public_message="Invalid token"
        )
