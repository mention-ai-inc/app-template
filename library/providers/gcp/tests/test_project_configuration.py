import json
from pathlib import Path

import pytest

from library_provider_gcp.cloud import tasks
from library_provider_gcp.cloud.constants import PROJECT_NUMBERS_BY_ID

ROOT = Path(__file__).resolve().parents[4]
CLOUD = (
    json.loads((ROOT / "project.json").read_text())["cloud_values"]
    if (ROOT / "project.json").exists()
    else {
        "operations_project_id": "acme-operations-0000",
        "feature_project_id": "acme-feature-0000",
        "production_project_id": "acme-production-0000",
        "operations_project_number": "000000000001",
        "feature_project_number": "000000000003",
        "production_project_number": "000000000002",
        "region": "us-central1",
    }
)


@pytest.mark.parametrize("environment", ["operations", "feature", "production"])
def test_runtime_project_number_matches_configuration(environment: str) -> None:
    assert PROJECT_NUMBERS_BY_ID[CLOUD[f"{environment}_project_id"]] == CLOUD[f"{environment}_project_number"]


@pytest.mark.parametrize("environment,prefix", [("feature", "demo"), ("production", "")])
def test_task_destination_uses_configured_project_number(
    monkeypatch: pytest.MonkeyPatch, environment: str, prefix: str
) -> None:
    monkeypatch.setattr(tasks, "get_project_id", lambda: CLOUD[f"{environment}_project_id"])
    monkeypatch.setenv("FEATURE_ENVIRONMENT", prefix)
    assert (
        tasks.Tasks().get_base_url(service="notes", pool="standard")
        == f"https://{prefix}notes-p-standard-{CLOUD[f'{environment}_project_number']}.{CLOUD['region']}.run.app"
    )
