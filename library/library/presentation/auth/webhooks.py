import os

from fastapi import Depends, Header, Request
from svix import WebhookVerificationError
from svix.webhooks import Webhook

from library.application.errors import ApplicationError, ApplicationErrorType


async def validate_clerk_webhook_signature(
    *,
    svix_id: str = Header(alias="svix-id"),
    svix_timestamp: str = Header(alias="svix-timestamp"),
    svix_signature: str = Header(alias="svix-signature"),
    svix_signing_secret: str = Depends(lambda: os.getenv("CLERK_WEBHOOK_SECRET")),
    request: Request,
) -> None:
    headers = {"svix-id": svix_id, "svix-timestamp": svix_timestamp, "svix-signature": svix_signature}
    webhook = Webhook(svix_signing_secret)
    request_body = await request.body()

    try:
        webhook.verify(request_body, headers)
    except WebhookVerificationError:
        raise ApplicationError(error_type=ApplicationErrorType.VALIDATION_ERROR, message="Invalid webhook signature")
