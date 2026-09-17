from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from mention_template import setup

pytestmark = pytest.mark.skipif(
    os.getenv("PROJECT_SETUP_REAL_EXPORTS") != "1", reason="Run m test-project-exports after syncing cloud branches"
)


def __export_cloud(cloud: str, tmp_path: Path) -> Path:
    destination = tmp_path / "example-product"
    setup.new_project(Path(__file__).resolve().parents[3], cloud, destination)
    metadata = setup.provider(destination)
    config = setup.load(destination / setup.CONFIG)
    config.update(domain="example.org", github_repository="example/product", display_name="Example Product")
    common = {
        "engineer_email": "engineer@example.org",
        "vercel_team_id": "team_example",
        "account_id": "123456789012",
        "bucket_prefix": "example-operations-1234",
        "billing_account_id": "ABCDEF-123456-ABCDEF",
        "region": {"gcp": "us-central1", "aws": "us-east-1", "azure": "eastus"}[cloud],
        "subscription_id": "12345678-1234-1234-1234-123456789012",
        "tenant_id": "22345678-1234-1234-1234-123456789012",
        "engineer_object_id": "32345678-1234-1234-1234-123456789012",
        "organization_id": "123456789012",
        "folder_id": "223456789012",
    }
    for environment in ("operations", "production", "feature"):
        common[f"{environment}_project_id"] = f"example-{environment}-1234"
        common[f"{environment}_project_number"] = {
            "operations": "123456789012",
            "feature": "223456789012",
            "production": "323456789012",
        }[environment]
        common[f"{environment}_name"] = f"example-{environment[:4]}-1234"
        common[f"{environment}_compact_name"] = f"example{environment[:4]}1234"
    config["cloud_values"] = {field["key"]: common[field["key"]] for field in metadata["fields"]}
    for environment in ("feature", "production"):
        config["clerk"][environment] = {
            "publishable_key": f"pk_{'test' if environment == 'feature' else 'live'}_example",
            "jwks_url": f"https://{environment}.example.org/.well-known/jwks.json",
        }
    setup.save(destination / setup.CONFIG, config)
    with patch.object(setup, "regenerate"):
        setup.configure(destination, True)
        setup.configure(destination, True)
    assert not (destination / "packages/acme-api/package.json").exists()
    assert (destination / "packages/example-product-api/src/api.d.ts").exists()
    assert "example-product-api" in (destination / "infrastructure/cli/local/compile-api").read_text()
    assert "CLERK_JWKS_URL" in (destination / "library/library/presentation/auth/direct.py").read_text()
    for path in (destination / "infrastructure/terraform").rglob("*.tf"):
        text = path.read_text()
        assert "pk_test_REPLACE_ME" not in text
        assert "pk_live_REPLACE_ME" not in text
        assert "acme.example.com" not in text
    if cloud == "gcp":
        constants = destination / "library/providers/gcp/library_provider_gcp/cloud/constants.py"
        for environment in ("operations", "feature", "production"):
            assert (
                f'{environment.upper()}_PROJECT_NUMBER = "{common[f"{environment}_project_number"]}"'
                in constants.read_text()
            )
        config["cloud_values"]["feature_project_number"] = "423456789012"
        setup.save(destination / setup.CONFIG, config)
        with patch.object(setup, "regenerate"):
            setup.configure(destination, True)
            setup.configure(destination, True)
        assert 'FEATURE_PROJECT_NUMBER = "423456789012"' in constants.read_text()
    if cloud == "azure":
        text = (destination / "infrastructure/cli/provider/helpers/acr-login").read_text()
        assert "TOKEN_LOGIN_USERNAME=00000000-0000-0000-0000-000000000000" in text
        base = (destination / "infrastructure/terraform/configurations/services/base.tf").read_text()
        assert common["subscription_id"] in base and common["tenant_id"] in base
    subprocess.run(
        [str(destination / "infrastructure/cli/_bin/m"), "sync-agent-parity"],
        cwd=destination,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [str(destination / "infrastructure/cli/_bin/m"), "check-agent-parity"],
        cwd=destination,
        check=True,
        capture_output=True,
    )
    for component in ("services", "admin"):
        values = json.loads(
            (destination / f"infrastructure/terraform/configurations/{component}/project.auto.tfvars.json").read_text()
        )
        assert values == {"enable_sentry": False, "enable_logfire": False}

    return destination


@pytest.mark.parametrize("cloud", ["gcp", "aws", "azure"])
def test_real_cloud_export(cloud: str, tmp_path: Path) -> None:
    __export_cloud(cloud, tmp_path)


@pytest.mark.parametrize("cloud", ["gcp", "aws", "azure"])
@pytest.mark.parametrize("failure", ["none", "deploy", "health"])
def test_minimal_deployment_and_failures(cloud: str, failure: str, tmp_path: Path) -> None:
    product = __export_cloud(cloud, tmp_path)
    provider_directory = product / "infrastructure/cli/provider/deployment"
    (provider_directory / "run-terraform").write_text('echo "terraform $*" >> "$RUN_TRACE"\n')
    deploy = provider_directory / "deploy"
    deploy.write_text('#!/bin/bash\necho "deploy $*" >> "$RUN_TRACE"\n[ "$FAIL_DEPLOY" != yes ]\n')
    deploy.chmod(0o755)
    fakebin = tmp_path / "bin"
    fakebin.mkdir()
    curl = fakebin / "curl"
    curl.write_text('#!/bin/bash\nprintf "%s" "$HEALTH_STATUS"\n')
    curl.chmod(0o755)
    trace = tmp_path / "trace"
    env = {
        **os.environ,
        "FEATURE_ENVIRONMENT": "demo",
        "PATH": f"{fakebin}:{os.environ['PATH']}",
        "RUN_TRACE": str(trace),
        "FAIL_DEPLOY": "yes" if failure == "deploy" else "no",
        "HEALTH_STATUS": "503" if failure == "health" else "200",
        "HEALTH_TIMEOUT_SECONDS": "0",
    }
    result = subprocess.run(
        [str(product / "infrastructure/cli/_bin/m"), "create-feature-environment"],
        cwd=product,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    steps = trace.read_text()
    assert "deploy notes" in steps
    assert "-f admin" not in steps and "-f mcp" not in steps
    assert ("-f web" in steps) == (failure != "deploy")
    assert (result.returncode == 0) == (failure == "none"), result.stderr
