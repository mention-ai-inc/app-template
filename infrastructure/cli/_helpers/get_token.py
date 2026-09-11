import asyncio
import os

import httpx

from library.presentation.auth.impersonation import generate_impersonation_token

TEST_USER_ID = os.getenv("TEST_CLERK_USER_ID", "user_abc123")
TEST_ORGANIZATION_ID = os.getenv("TEST_CLERK_ORGANIZATION_ID", "org_abc123")


async def main() -> None:
    try:
        token = await generate_impersonation_token(
            calling_service="notes",
            user_id=TEST_USER_ID,
            organization_id=TEST_ORGANIZATION_ID,
        )
    except httpx.HTTPStatusError as error:
        if error.response.status_code == 404:
            print("This feature environment does not exist yet, or the requested service does not exist within it.")
            return
        else:
            raise

    print(token)


if __name__ == "__main__":
    asyncio.run(main())
