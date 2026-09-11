"""Top-level orchestration: provision the organization and its admin in Clerk, then drive the product
through its REST API as that admin.

The seed runs as a *client*: it never modifies a service or the library. Everything it writes goes
through the deployed API, so the seeded data is exactly what a real user would have produced.
"""

from __future__ import annotations

import os

from admin.common.clerk import ClerkSeedClient
from admin.common.environment import require_feature_environment
from admin.common.logger import logger
from admin.seed.auth import mint_impersonation_token
from admin.seed.clients import build_client
from admin.seed.phases.notes import run_notes_phase
from admin.seed.state import load_state, save_state
from library.domain.value_objects.users import OrganizationID, UserID
from library.infrastructure.cloud.constants import DOMAIN

_REQUIRED_ENV = ("GOOGLE_CLOUD_PROJECT", "CLERK_SECRET_KEY")

SEED_ADMIN_EMAIL = f"seed.admin+clerk_test@{DOMAIN}"
SEED_ORGANIZATION_NAME = "Seed Organization"
ADMIN_ROLE = "org:admin"


async def run_seed(*, organization_id: str | None) -> None:
    feature_environment = require_feature_environment()
    missing = [name for name in _REQUIRED_ENV if not os.getenv(name)]
    if missing:
        raise SystemExit(f"Missing required environment: {', '.join(missing)}")

    clerk = ClerkSeedClient()
    state = load_state(feature_environment)

    admin_user_id = await clerk.get_or_create_user(email=SEED_ADMIN_EMAIL, first_name="Seed", last_name="Admin")
    resolved_organization_id = await _resolve_organization(
        clerk=clerk, requested=organization_id or state.organization_id, admin_user_id=admin_user_id
    )
    await clerk.add_to_organization(organization_id=resolved_organization_id, user_id=admin_user_id, role=ADMIN_ROLE)
    state.organization_id = str(resolved_organization_id)
    state.admin_user_id = str(admin_user_id)
    save_state(feature_environment, state)
    logger.info("Seeding organization %s as %s", resolved_organization_id, admin_user_id)

    token = await mint_impersonation_token(organization_id=resolved_organization_id, user_id=admin_user_id)
    async with build_client(
        feature_environment=feature_environment,
        organization_id=resolved_organization_id,
        admin_user_id=admin_user_id,
        token=token,
    ) as client:
        await run_notes_phase(client=client)

    logger.info("=== Seed run complete for %s ===", resolved_organization_id)


async def _resolve_organization(
    *, clerk: ClerkSeedClient, requested: str | None, admin_user_id: UserID
) -> OrganizationID:
    if requested is not None:
        return OrganizationID(requested)
    organization_id = await clerk.create_organization(name=SEED_ORGANIZATION_NAME, created_by=admin_user_id)
    logger.info("Created organization %s", organization_id)
    return organization_id
