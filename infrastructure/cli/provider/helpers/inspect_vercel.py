from __future__ import annotations

import http.client
import json
import re
import subprocess
import sys
from pathlib import Path


class VerificationError(Exception):
    pass


def main() -> int:
    config = json.loads(Path("project.json").read_text())
    if not config["cloud_values"]["engineer_email"] or not config["cloud_values"]["operations_project_id"]:
        raise VerificationError("Configure the project and engineer identity before credential verification.")
    cloud = config["cloud_values"]
    team_id = cloud["vercel_team_id"]
    if not re.fullmatch(r"team_[A-Za-z0-9]+", team_id):
        raise VerificationError("Configure a valid Vercel team ID in project.json.")
    result = subprocess.run(
        [
            "gcloud",
            "secrets",
            "versions",
            "access",
            "latest",
            "--secret=VERCEL_TERRAFORM_API_KEY",
            f"--project={cloud['operations_project_id']}",
            f"--account={cloud['engineer_email']}",
            "--quiet",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode or not result.stdout.strip():
        raise VerificationError("Cannot access a nonempty operations VERCEL_TERRAFORM_API_KEY.")
    connection = http.client.HTTPSConnection("api.vercel.com", timeout=30)
    try:
        connection.request(
            "GET",
            f"/v2/teams/{team_id}",
            headers={"Authorization": f"Bearer {result.stdout.strip()}"},
        )
        response = connection.getresponse()
        if response.status != 200:
            raise VerificationError(f"Vercel team lookup returned HTTP {response.status}; response body withheld.")
        team = json.loads(response.read())
    finally:
        connection.close()
    if team.get("id") != team_id:
        raise VerificationError("Vercel returned a different team ID.")
    print("PASS stored Vercel token authenticates to the configured team; no secret value was printed.")
    print("MANUAL project creation and deployment permissions remain unverified until the approved deployment.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except VerificationError as error:
        print(f"BLOCKED {error}")
        sys.exit(1)
    except (ValueError, KeyError, TypeError, OSError, subprocess.TimeoutExpired, http.client.HTTPException):
        print("BLOCKED Vercel verification failed; check configuration, secret access, and API connectivity.")
        sys.exit(1)
