from __future__ import annotations

import argparse
import ast
import contextlib
import io
import json
import subprocess
from pathlib import Path
from typing import Any

import inspect_clerk
import inspect_vercel


class DiagnosticError(Exception):
    pass


def command(*arguments: str) -> str:
    result = subprocess.run(arguments, capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise DiagnosticError("Read-only command failed; check configured identity and access.")
    return result.stdout.strip()


def routing(config: dict[str, Any], root: Path) -> list[dict[str, str]]:
    tree = ast.parse((root / "library/providers/gcp/library_provider_gcp/cloud/constants.py").read_text())
    constants = {
        statement.targets[0].id: statement.value.value
        for statement in tree.body
        if isinstance(statement, ast.Assign)
        and isinstance(statement.targets[0], ast.Name)
        and isinstance(statement.value, ast.Constant)
    }
    checks = []
    for environment in ("operations", "feature", "production"):
        matches = all(
            config["cloud_values"].get(f"{environment}_{field}")
            and constants.get(f"{environment}_{field}".upper()) == config["cloud_values"][f"{environment}_{field}"]
            for field in ("project_id", "project_number")
        )
        checks.append(
            {
                "check": f"{environment}-runtime-routing",
                "status": "pass" if matches else "blocked",
                "detail": "Runtime identity matches configuration"
                if matches
                else "Configure assigned project identifiers and regenerate runtime constants.",
            }
        )
    return checks


def credential_checks(name: str) -> list[dict[str, str]]:
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stdout(buffer):
            if name == "clerk":
                inspect_clerk.main()
            else:
                inspect_vercel.main()
    except Exception:
        return [
            {
                "check": name,
                "status": "blocked",
                "detail": "Credential verification failed; run m inspect-" + name + ". Secret values are withheld.",
            }
        ]
    checks = []
    for line in buffer.getvalue().splitlines():
        status, _, detail = line.partition(" ")
        if status in ("PASS", "BLOCKED", "MANUAL"):
            checks.append({"check": name, "status": status.lower(), "detail": detail})
    return checks or [{"check": name, "status": "blocked", "detail": "Credential verification returned no checks."}]


def prerequisites(config: dict[str, Any], root: Path) -> list[dict[str, str]]:
    cloud = config["cloud_values"]
    checks = []
    try:
        nameservers = json.loads(
            command(
                "gcloud",
                "dns",
                "managed-zones",
                "describe",
                config["slug"],
                f"--project={cloud['operations_project_id']}",
                f"--account={cloud['engineer_email']}",
                "--format=json(nameServers)",
                "--quiet",
            )
        )["nameServers"]
        public = command("dig", "+short", "NS", config["domain"]).splitlines()
        matches = bool(nameservers) and set(nameservers) == set(public)
        checks.append(
            {
                "check": "dns-delegation",
                "status": "pass" if matches else "blocked",
                "detail": "Public nameservers match the assigned zone."
                if matches
                else "Delegate the subdomain to the assigned nameservers.",
            }
        )
    except Exception:
        checks.append(
            {"check": "dns-delegation", "status": "blocked", "detail": "Cannot verify configured DNS delegation."}
        )
    manifest = json.loads(
        (root / "infrastructure/terraform/modules/compute-engine-redis/cache-images.json").read_text()
    )
    for image in manifest.values():
        try:
            reference = f"{cloud['region']}-docker.pkg.dev/{cloud['operations_project_id']}/public-images/{image['name']}:{image['version']}"
            result = json.loads(
                command(
                    "gcloud",
                    "artifacts",
                    "docker",
                    "images",
                    "describe",
                    reference,
                    f"--account={cloud['engineer_email']}",
                    "--format=json(image_summary.digest)",
                    "--quiet",
                )
            )
            matches = result["image_summary"]["digest"] == image["digest"]
            checks.append(
                {
                    "check": image["name"],
                    "status": "pass" if matches else "blocked",
                    "detail": "Published digest matches pinned image."
                    if matches
                    else "Published digest differs from pinned image.",
                }
            )
        except Exception:
            checks.append(
                {
                    "check": image["name"],
                    "status": "blocked",
                    "detail": "Publish the required cache image before provisioning the cache VM.",
                }
            )
    return checks


def diagnose(config: dict[str, Any], root: Path, stage: str) -> list[dict[str, str]]:
    if stage == "prerequisites":
        return prerequisites(config, root)
    checks = routing(config, root)
    if stage == "local":
        return checks
    cloud = config["cloud_values"]
    for environment in ("operations", "feature", "production"):
        try:
            project = cloud[f"{environment}_project_id"]
            number = cloud[f"{environment}_project_number"]
            if not project or not number:
                raise DiagnosticError("Missing assigned identifiers")
            actual = command(
                "gcloud",
                "projects",
                "describe",
                project,
                f"--account={cloud['engineer_email']}",
                "--format=value(projectNumber)",
                "--quiet",
            )
            matches = actual == number
            checks.append(
                {
                    "check": f"{environment}-cloud-identity",
                    "status": "pass" if matches else "blocked",
                    "detail": "Cloud project number matches configuration."
                    if matches
                    else "Configured project number does not match Google Cloud.",
                }
            )
        except Exception:
            checks.append(
                {
                    "check": f"{environment}-cloud-identity",
                    "status": "blocked",
                    "detail": "Configure assigned identifiers and verify project access.",
                }
            )
    checks.extend(credential_checks("clerk"))
    checks.extend(credential_checks("vercel"))
    if stage == "demo":
        checks.extend(prerequisites(config, root))
    return checks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("local", "cloud", "demo", "prerequisites"), required=True)
    parser.add_argument("--text", action="store_true")
    args = parser.parse_args()
    try:
        checks = diagnose(json.loads(Path("project.json").read_text()), Path.cwd(), args.stage)
    except Exception:
        checks = [
            {
                "check": "provider",
                "status": "blocked",
                "detail": "Cannot inspect configured GCP environment; diagnostic payload withheld.",
            }
        ]
    if args.text:
        for check in checks:
            print(f"{check['status'].upper()} {check['check']}: {check['detail']}")
        return int(any(check["status"] == "blocked" for check in checks))
    print(json.dumps(checks))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
