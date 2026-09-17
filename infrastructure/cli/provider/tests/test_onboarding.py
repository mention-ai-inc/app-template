from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from infrastructure.cli.provider.helpers import demo_note, doctor, inspect_clerk, inspect_vercel

ROOT = Path(__file__).resolve().parents[4]


@pytest.fixture
def config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    settings = {
        "slug": "example",
        "domain": "example.org",
        "cloud": "gcp",
        "cloud_values": {
            "engineer_email": "engineer@example.org",
            "organization_id": "123456789012",
            "folder_id": "",
            "billing_account_id": "AAAAAA-BBBBBB-CCCCCC",
            "region": "us-central1",
            "vercel_team_id": "team_example",
            "operations_project_id": "example-operations",
            "operations_project_number": "123456789012",
            "feature_project_id": "example-feature",
            "feature_project_number": "223456789012",
            "production_project_id": "example-production",
            "production_project_number": "323456789012",
        },
        "clerk": {
            "feature": {
                "publishable_key": "pk_test_ZXhhbXBsZS5vcmck",
                "jwks_url": "https://example.org/.well-known/jwks.json",
            }
        },
    }
    (tmp_path / "project.json").write_text(json.dumps(settings))
    monkeypatch.chdir(tmp_path)
    return settings


def test_routing_detects_swapped_project_numbers(config: dict[str, Any], tmp_path: Path) -> None:
    constants = tmp_path / "library/providers/gcp/library_provider_gcp/cloud/constants.py"
    constants.parent.mkdir(parents=True)
    constants.write_text(
        "\n".join(f'{key.upper()} = "{value}"' for key, value in config["cloud_values"].items() if "project" in key)
    )
    assert all(check["status"] == "pass" for check in doctor.routing(config, tmp_path))
    constants.write_text(
        constants.read_text().replace(
            'FEATURE_PROJECT_NUMBER = "223456789012"', 'FEATURE_PROJECT_NUMBER = "323456789012"'
        )
    )
    assert any(
        check["check"] == "feature-runtime-routing" and check["status"] == "blocked"
        for check in doctor.routing(config, tmp_path)
    )


def test_cloud_identity_mismatch_and_local_offline(config: dict[str, Any], tmp_path: Path) -> None:
    with (
        patch.object(doctor, "routing", return_value=[]),
        patch.object(doctor, "credential_checks", return_value=[]),
        patch.object(doctor, "command", return_value="wrong") as command,
    ):
        assert doctor.diagnose(config, tmp_path, "local") == []
        command.assert_not_called()
        result = doctor.diagnose(config, tmp_path, "cloud")
    assert all(check["status"] == "blocked" for check in result)


@pytest.mark.parametrize("module", [inspect_clerk, inspect_vercel])
@pytest.mark.usefixtures("config")
def test_unavailable_credentials_are_redacted(module: Any, capsys: pytest.CaptureFixture[str]) -> None:
    response = MagicMock()
    response.__enter__.return_value.read.return_value = json.dumps(
        {"keys": [{"kid": "1", "kty": "RSA", "n": "n", "e": "e"}]}
    ).encode()
    with (
        patch.object(inspect_clerk.urllib.request, "urlopen", return_value=response),
        patch.object(
            module.subprocess,
            "run",
            return_value=subprocess.CompletedProcess([], 1, "private-key-value", "private-error"),
        ),
    ):
        with pytest.raises(module.VerificationError) as error:
            module.main()
    assert "private" not in str(error.value) + capsys.readouterr().out


@pytest.mark.usefixtures("config")
def test_vercel_wrong_team_is_rejected() -> None:
    connection = MagicMock()
    response = connection.getresponse.return_value
    response.status = 200
    response.read.return_value = b'{"id":"team_other"}'
    with (
        patch.object(inspect_vercel.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "secret", "")),
        patch.object(inspect_vercel.http.client, "HTTPSConnection", return_value=connection),
    ):
        with pytest.raises(inspect_vercel.VerificationError, match="different team"):
            inspect_vercel.main()


def test_manual_credential_checks_remain_manual() -> None:
    with patch.object(doctor.inspect_clerk, "main", side_effect=lambda: print("MANUAL confirm Organizations")):
        assert doctor.credential_checks("clerk")[0]["status"] == "manual"


def test_recovery_only_resets_dispatch_metadata() -> None:
    transaction = MagicMock()
    note_reference = MagicMock()
    command_reference = MagicMock()
    note_reference.get.return_value.to_dict.return_value = {"status": "summarizing", "summary": None}
    command_reference.get.return_value.to_dict.return_value = {
        "organization_id": "org_example",
        "payload": {"note_id": "note"},
        "name": "SummarizeNote",
        "processed_at": None,
        "dispatched_at": "earlier",
    }
    demo_note.retry_command.to_wrap(transaction, note_reference, command_reference, "org_example", "note")
    transaction.update.assert_called_once_with(command_reference, {"dispatched_at": None})


@pytest.mark.parametrize("completed", ["note", "command", "organization"])
def test_recovery_rechecks_concurrent_completion(completed: str) -> None:
    transaction = MagicMock()
    note_reference = MagicMock()
    command_reference = MagicMock()
    note_reference.get.return_value.to_dict.return_value = {
        "status": "summarized" if completed == "note" else "summarizing",
        "summary": None,
    }
    command_reference.get.return_value.to_dict.return_value = {
        "organization_id": "wrong" if completed == "organization" else "org_example",
        "payload": {"note_id": "note"},
        "name": "SummarizeNote",
        "processed_at": "now" if completed == "command" else None,
        "dispatched_at": "earlier",
    }
    with pytest.raises(demo_note.VerificationError):
        demo_note.retry_command.to_wrap(transaction, note_reference, command_reference, "org_example", "note")
    transaction.update.assert_not_called()


@pytest.mark.parametrize("environment", ["", "production", "../demo"])
@pytest.mark.usefixtures("config")
def test_recovery_rejects_production_before_database_access(environment: str) -> None:
    with (
        patch.object(
            sys,
            "argv",
            ["demo-note", "--organization-id", "org_example", "--note-id", "note", "--environment", environment],
        ),
        patch.object(demo_note.firestore, "Client") as client,
    ):
        with pytest.raises(demo_note.VerificationError):
            demo_note.main()
        client.assert_not_called()


@pytest.mark.parametrize("count", [0, 2])
@pytest.mark.usefixtures("config")
def test_recovery_requires_one_command(count: int) -> None:
    client = MagicMock()
    note = client.collection.return_value.document.return_value.get.return_value
    note.exists = True
    note.to_dict.return_value = {"organization_id": "org_example", "status": "summarizing", "summary": None}
    command = MagicMock()
    command.id = "command"
    command.to_dict.return_value = {
        "organization_id": "org_example",
        "name": "SummarizeNote",
        "dispatched_at": "earlier",
        "processed_at": None,
    }
    client.collection.return_value.where.return_value.select.return_value.limit.return_value.stream.return_value = [
        command
    ] * count
    with (
        patch.object(sys, "argv", ["demo-note", "--organization-id", "org_example", "--note-id", "note", "--retry"]),
        patch.object(demo_note.firestore, "Client", return_value=client),
        pytest.raises(demo_note.VerificationError, match="exactly one"),
    ):
        demo_note.main()


@pytest.mark.usefixtures("config")
def test_missing_note_is_reported() -> None:
    client = MagicMock()
    client.collection.return_value.document.return_value.get.return_value.exists = False
    with (
        patch.object(sys, "argv", ["demo-note", "--organization-id", "org_example", "--note-id", "missing"]),
        patch.object(demo_note.firestore, "Client", return_value=client),
        pytest.raises(demo_note.VerificationError, match="does not exist"),
    ):
        demo_note.main()


@pytest.mark.usefixtures("config")
def test_bootstrap_preview_never_calls_cloud(tmp_path: Path) -> None:
    before = (tmp_path / "project.json").read_bytes()
    result = subprocess.run(
        ["bash", str(ROOT / "infrastructure/cli/provider/bootstrap-foundation")], capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "billing.admin" in result.stdout
    assert before == (tmp_path / "project.json").read_bytes()


def test_image_manifest_is_used_by_terraform_and_publication() -> None:
    directory = ROOT / "infrastructure/terraform/modules/compute-engine-redis"
    manifest = json.loads((directory / "cache-images.json").read_text())
    assert all(
        image["platform"] == "linux/amd64" and image["digest"].startswith("sha256:") for image in manifest.values()
    )
    assert (
        'jsondecode(file("${path.module}/cache-images.json"))' in (directory / "google_compute_instance.tf").read_text()
    )
    assert "cache-images.json" in (ROOT / "infrastructure/cli/provider/onboarding.mk").read_text()


def test_failed_command_does_not_expose_payload() -> None:
    with (
        patch.object(doctor.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, "secret", "secret")),
        pytest.raises(doctor.DiagnosticError) as error,
    ):
        doctor.command("unused")
    assert "secret" not in str(error.value)


@pytest.mark.usefixtures("config")
@pytest.mark.parametrize("mismatch", ["none", "instance", "claims"])
def test_clerk_instance_and_claims(mismatch: str) -> None:
    public_keys = {"keys": [{"kid": "1", "kty": "RSA", "n": "n", "e": "e"}]}
    response = MagicMock()
    response.__enter__.return_value.read.return_value = json.dumps(public_keys).encode()
    claims = dict(inspect_clerk.EXPECTED_CLAIMS)
    if mismatch == "claims":
        claims.pop("organization_id")
    backend_keys = (
        {"keys": [{"kid": "other", "kty": "RSA", "n": "other", "e": "e"}]} if mismatch == "instance" else public_keys
    )
    with (
        patch.object(inspect_clerk.urllib.request, "urlopen", return_value=response),
        patch.object(
            inspect_clerk.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "sk_test_private", "")
        ),
        patch.object(
            inspect_clerk,
            "clerk_get",
            side_effect=[backend_keys, [{"name": "main", "claims": claims, "custom_signing_key": False}]],
        ),
    ):
        if mismatch == "instance":
            with pytest.raises(inspect_clerk.VerificationError, match="different Clerk"):
                inspect_clerk.main()
        else:
            assert inspect_clerk.main() == (1 if mismatch == "claims" else 0)


def test_local_routing_waits_for_unassigned_projects(config: dict[str, Any], tmp_path: Path) -> None:
    constants = tmp_path / "library/providers/gcp/library_provider_gcp/cloud/constants.py"
    constants.parent.mkdir(parents=True)
    constants.write_text("")
    for environment in ("operations", "feature", "production"):
        config["cloud_values"][f"{environment}_project_number"] = ""
    assert all(check["status"] == "manual" for check in doctor.routing(config, tmp_path))
