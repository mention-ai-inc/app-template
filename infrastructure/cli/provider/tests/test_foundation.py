from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]


@pytest.fixture
def foundation(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    config = {
        "cloud": "gcp",
        "slug": "example",
        "cloud_values": {
            "engineer_email": "engineer@example.org",
            "organization_id": "123456789012",
            "folder_id": "",
            "billing_account_id": "AAAAAA-BBBBBB-CCCCCC",
            "operations_project_id": "example-operations",
            "operations_project_number": "",
            "region": "us-central1",
        },
    }
    (tmp_path / "project.json").write_text(json.dumps(config))
    binary = tmp_path / "bin"
    binary.mkdir()
    cloud = binary / "gcloud"
    cloud.write_bytes((ROOT / "infrastructure/cli/provider/tests/fake_cloud.py").read_bytes())
    cloud.chmod(0o755)
    sleep = binary / "sleep"
    sleep.write_text("#!/bin/sh\nexit 0\n")
    sleep.chmod(0o755)
    return tmp_path, {
        **os.environ,
        "PATH": f"{binary}:{os.environ['PATH']}",
        "FAKE_STATE": str(tmp_path / "cloud.json"),
    }


def apply(foundation: tuple[Path, dict[str, str]], mode: str = "") -> subprocess.CompletedProcess[str]:
    directory, environment = foundation
    return subprocess.run(
        ["bash", str(ROOT / "infrastructure/cli/provider/bootstrap-foundation"), "--apply"],
        cwd=directory,
        env={**environment, "FAKE_MODE": mode},
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_fresh_and_repeated_foundation_reuses_resources(foundation: tuple[Path, dict[str, str]]) -> None:
    assert apply(foundation).returncode == 0
    directory, environment = foundation
    before = json.loads(Path(environment["FAKE_STATE"]).read_text())
    assert (
        json.loads((directory / "project.json").read_text())["cloud_values"]["operations_project_number"]
        == "123456789012"
    )
    assert apply(foundation).returncode == 0
    after = json.loads(Path(environment["FAKE_STATE"]).read_text())
    assert not any(
        "create" in call or "add-iam-policy-binding" in call for call in after["calls"][len(before["calls"]) :]
    )


def test_interrupted_foundation_resumes(foundation: tuple[Path, dict[str, str]]) -> None:
    assert apply(foundation, "interrupted").returncode != 0
    assert apply(foundation).returncode == 0


@pytest.mark.parametrize("mode", ["ambiguous", "billing", "bucket", "identity_timeout"])
def test_foundation_conflicts_and_timeout_stop(foundation: tuple[Path, dict[str, str]], mode: str) -> None:
    result = apply(foundation, mode)
    assert result.returncode != 0
    assert "private-test-token" not in result.stdout + result.stderr
    if mode == "identity_timeout":
        assert "existing resources will be reused" in result.stderr
