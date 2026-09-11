import functools
import logging
import os

import httpx
import jwt
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from library.infrastructure.cloud.iam import IAM
from library.infrastructure.cloud.project import get_project_id
from library.infrastructure.users import ClerkRole
from library.logs import SIMPLE_LOGGER_NAME
from library.presentation.auth.types import AuthenticatedUser
from library.presentation.errors import PresentationError, PresentationErrorType

logger = logging.getLogger(SIMPLE_LOGGER_NAME)
iam = IAM()


def __load_public_key_from_x509(certificate: str) -> bytes:
    cert = x509.load_pem_x509_certificate(certificate.encode(), default_backend())
    public_key = cert.public_key()
    pem_public_key = public_key.public_bytes(
        encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return pem_public_key


@functools.cache
def __get_public_keys(*, service_account_email: str) -> dict[str, str]:
    response = httpx.get(f"https://www.googleapis.com/robot/v1/metadata/x509/{service_account_email}")
    return response.json()


async def generate_impersonation_token(*, calling_service: str, user_id: str, organization_id: str) -> str:
    service_account_email = (
        f"{os.getenv('FEATURE_ENVIRONMENT', '')}{calling_service}-s@{get_project_id()}.iam.gserviceaccount.com"
    )
    generated_jwt = await iam.sign_jwt(
        service_account_email=service_account_email,
        payload={
            "iss": service_account_email,
            "uid": user_id,
            "organization_id": organization_id,
            "clerk_role": ClerkRole.ADMIN,
            "impersonating_service": calling_service,
            "organization_public_metadata": {os.getenv("FEATURE_ENVIRONMENT", ""): {}},
        },
    )
    return generated_jwt.signed_jwt


def get_impersonated_user(*, token: HTTPAuthorizationCredentials = Depends(HTTPBearer())) -> AuthenticatedUser:
    try:
        headers = jwt.get_unverified_header(token.credentials)
        unverified_token = jwt.decode(token.credentials, options={"verify_signature": False})

        public_keys = __get_public_keys(service_account_email=unverified_token["iss"])
        public_key = __load_public_key_from_x509(public_keys[headers["kid"]])

        decoded_token = jwt.decode(token.credentials, public_key, algorithms=headers["alg"])
        user = AuthenticatedUser.model_validate({**decoded_token, "token": token.credentials})

        return user
    except Exception as error:
        raise PresentationError(
            error_type=PresentationErrorType.AUTHENTICATION_ERROR, message=str(error), public_message="Invalid token"
        )
