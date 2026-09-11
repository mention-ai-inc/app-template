"""HTTP client for the admin API at https://{env}admin.{DOMAIN}.

The CLI is a thin client over the IAP-gated admin API: commands run from a laptop or CI call the
API, while the same commands executed inside a Cloud Run job (detected via the `CLOUD_RUN_JOB`
environment variable Cloud Run sets) run their workers directly against the stores. Authentication
impersonates the terraform service account (the one non-human IAP accessor in every feature
environment) through the IAM credentials API, minting an ID token whose audience is the target
project's IAP OAuth client, or uses a pre-minted token in `IAP_ID_TOKEN`. Production IAP excludes
service accounts by design, so production commands run the Cloud Run job directly. Tokens are minted
per request because job-launching commands poll longer than a token's lifetime.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx

from admin.common.environment import feature_environment, project_for
from library.infrastructure.cloud.constants import DOMAIN, OPERATIONS_PROJECT_ID, PRODUCTION_PROJECT_ID, REGION
from library.infrastructure.cloud.iam import IAM
from library.infrastructure.cloud.secretmanager import SecretManager

POLL_INTERVAL_SECONDS = 10
REQUEST_TIMEOUT_SECONDS = 120
TERMINAL_STATUSES = ("succeeded", "failed")
IAP_SERVICE_ACCOUNT = f"terraform@{OPERATIONS_PROJECT_ID}.iam.gserviceaccount.com"
IAP_CLIENT_ID_SECRET = "ADMIN_IAP_OAUTH_CLIENT_ID"


def runs_in_job() -> bool:
    return bool(os.getenv("CLOUD_RUN_JOB"))


async def mint_identity_token() -> str:
    token = os.getenv("IAP_ID_TOKEN")
    if token:
        return token
    environment = feature_environment()
    if not environment:
        raise SystemExit(
            "Production IAP admits no service accounts, so `m admin` cannot reach it. "
            "Execute the Cloud Run job directly: "
            f"`gcloud run jobs execute admin-j-backfill --project {PRODUCTION_PROJECT_ID} --region {REGION} "
            '--args="run,<name>,--apply" --wait`.'
        )
    audience = await SecretManager(project=project_for(environment)).access_secret_version(
        secret_id=IAP_CLIENT_ID_SECRET
    )
    return await IAM().generate_id_token(service_account_email=IAP_SERVICE_ACCOUNT, audience=audience)


class AdminClient:
    def __init__(self, *, base_url: str | None = None, token: str | None = None) -> None:
        self._base_url = base_url or f"https://{feature_environment()}admin.{DOMAIN}"
        self._token_override = token

    async def get(self, path: str) -> Any:
        return await self.__request("GET", path)

    async def post(self, path: str, body: dict[str, Any]) -> Any:
        return await self.__request("POST", path, body=body)

    async def wait_for_run(self, execution_id: str) -> dict[str, Any]:
        last_status = ""
        while True:
            run: dict[str, Any] = await self.get(f"/runs/{execution_id}")
            if run["status"] != last_status:
                last_status = run["status"]
                print(f"  {last_status}")
            if run["status"] in TERMINAL_STATUSES:
                return run
            await asyncio.sleep(POLL_INTERVAL_SECONDS)

    async def print_run_logs(self, execution_id: str) -> None:
        logs: dict[str, Any] = await self.get(f"/runs/{execution_id}/logs")
        for line in logs["lines"]:
            print(f"  {line['message']}")

    async def __request(self, method: str, path: str, *, body: dict[str, Any] | None = None) -> Any:
        token = self._token_override or await mint_identity_token()
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.request(
                method,
                f"{self._base_url}{path}",
                json=body,
                headers={"Authorization": f"Bearer {token}"},
            )
        if response.status_code >= 400:
            raise SystemExit(f"{method} {path} failed ({response.status_code}): {_error_detail(response)}")
        return response.json()


async def launch_and_follow(path: str, body: dict[str, Any]) -> dict[str, Any]:
    client = AdminClient()
    response = await client.post(path, body)
    execution_id: str = response["execution_id"]
    print(f"Execution: {execution_id}")
    run = await client.wait_for_run(execution_id)
    await client.print_run_logs(execution_id)
    if run["status"] != "succeeded":
        raise SystemExit(1)
    return run


def _error_detail(response: httpx.Response) -> str:
    try:
        return str(response.json().get("detail", response.text))
    except ValueError:
        return response.text
