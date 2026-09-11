import asyncio
import os

from library.infrastructure.users import ClerkClient

feature_environment = os.environ["FEATURE_ENVIRONMENT"]


async def clear_clerk_metadata_async() -> None:
    """Clear metadata from all organizations and users in the feature environment."""
    clerk = ClerkClient()

    organizations = await clerk.list_organizations()
    for organization in organizations:
        print(f"Clearing metadata for organization {organization.id}")
        await clerk.clear_organization_metadata(organization_id=organization.id)

        user_ids = await clerk.list_organization_member_user_ids(organization_id=organization.id)
        for user_id in user_ids:
            print(f"Clearing metadata for user {user_id} in organization {organization.id}")
            await clerk.clear_user_metadata(user_id=user_id, organization_id=organization.id)


if __name__ == "__main__":
    asyncio.run(clear_clerk_metadata_async())
