from __future__ import annotations

import base64
import http.client
import json
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

EXPECTED_CLAIMS = {
    "uid": "{{user.id}}",
    "organization_id": "{{org.id}}",
    "clerk_role": "{{org.role}}",
    "organization_public_metadata": "{{org.public_metadata}}",
}


class VerificationError(Exception):
    pass


def clerk_get(secret: str, path: str) -> Any:
    connection = http.client.HTTPSConnection("api.clerk.com", timeout=30)
    try:
        connection.request("GET", f"/v1/{path}", headers={"Authorization": f"Bearer {secret}"})
        response = connection.getresponse()
        if response.status != 200:
            raise VerificationError(f"Clerk {path} returned HTTP {response.status}; no response body was printed.")
        return json.loads(response.read())
    finally:
        connection.close()


def signing_keys(jwks: dict[str, Any]) -> set[tuple[str, str, str]]:
    return {
        (key["kid"], key["n"], key["e"])
        for key in jwks["keys"]
        if key.get("kty") == "RSA" and all(key.get(field) for field in ("kid", "n", "e"))
    }


def main() -> int:
    config = json.loads(Path("project.json").read_text())
    if not config["cloud_values"]["engineer_email"] or not config["cloud_values"]["feature_project_id"]:
        raise VerificationError("Configure the project and engineer identity before credential verification.")
    feature = config["clerk"]["feature"]
    publishable_key = feature["publishable_key"]
    if not publishable_key.startswith("pk_test_"):
        raise VerificationError("The feature instance must have a Clerk development publishable key.")
    encoded_host = publishable_key.removeprefix("pk_test_")
    host = base64.urlsafe_b64decode(encoded_host + "=" * (-len(encoded_host) % 4)).decode().rstrip("$")
    url = urllib.parse.urlparse(feature["jwks_url"])
    if url.scheme != "https" or url.netloc != host or url.path != "/.well-known/jwks.json":
        raise VerificationError("The publishable key and HTTPS JWKS endpoint must identify the same Clerk instance.")
    with urllib.request.urlopen(feature["jwks_url"], timeout=30) as response:
        public_jwks = json.load(response)
    public_keys = signing_keys(public_jwks)
    if not public_keys or public_jwks["keys"][0].get("kty") != "RSA":
        raise VerificationError("The JWKS endpoint must provide the RSA signing key used by the API.")
    print("PASS publishable key and live JWKS endpoint match.")

    secret_result = subprocess.run(
        [
            "gcloud",
            "secrets",
            "versions",
            "access",
            "latest",
            "--secret=CLERK_SECRET_KEY",
            f"--project={config['cloud_values']['feature_project_id']}",
            f"--account={config['cloud_values']['engineer_email']}",
            "--quiet",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if secret_result.returncode:
        raise VerificationError("Cannot access feature CLERK_SECRET_KEY; no secret output was printed.")
    secret = secret_result.stdout.strip()
    if not secret.startswith("sk_test_"):
        raise VerificationError("Feature CLERK_SECRET_KEY must be a development key.")
    if not public_keys.intersection(signing_keys(clerk_get(secret, "jwks"))):
        raise VerificationError("The stored secret key belongs to a different Clerk instance.")
    print("PASS stored secret authenticates to the matching development instance; no secret value was printed.")

    templates = clerk_get(secret, "jwt_templates")
    main_templates = [template for template in templates if template.get("name") == "main"]
    if len(main_templates) != 1:
        print("BLOCKED create the main JWT template using docs/getting-started.md.")
        return 1
    template = main_templates[0]
    mismatched = [name for name, value in EXPECTED_CLAIMS.items() if template.get("claims", {}).get(name) != value]
    if mismatched or template.get("custom_signing_key"):
        print(
            f"BLOCKED main JWT template: check claims {', '.join(mismatched) or 'none'} and use instance signing keys."
        )
        return 1
    print("PASS main JWT template includes the required claims and uses instance signing keys.")
    try:
        with urllib.request.urlopen(f"https://{host}/v1/environment", timeout=30) as response:
            environment = json.load(response)
        settings = environment.get("response", environment)
        organizations_enabled = settings.get("organization_settings", {}).get("enabled")
        first_factors = settings.get("user_settings", {}).get("sign_in", {}).get("first_factors")
        if not first_factors:
            first_factors = settings.get("auth_config", {}).get("first_factors")
    except (OSError, ValueError, KeyError, TypeError):
        organizations_enabled = None
        first_factors = None
    if organizations_enabled is False:
        print("BLOCKED Organizations are disabled in the public Clerk settings.")
        return 1
    if organizations_enabled is True:
        print("PASS Organizations are enabled.")
    else:
        print("MANUAL confirm Organizations are enabled in Clerk.")
    if isinstance(first_factors, list) and first_factors:
        print("PASS Clerk advertises at least one sign-in method.")
    else:
        print("MANUAL confirm a sign-in method is enabled in Clerk.")
    print("MANUAL complete the signed-in organization, note, and summary walkthrough after deployment.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except VerificationError as error:
        print(f"BLOCKED {error}")
        sys.exit(1)
    except (ValueError, KeyError, TypeError, OSError, subprocess.TimeoutExpired, http.client.HTTPException):
        print("BLOCKED Clerk verification failed; check the configured keys, endpoint, API access, and template.")
        sys.exit(1)
