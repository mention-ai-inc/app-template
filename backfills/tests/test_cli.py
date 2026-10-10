from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from backfills import cli
from backfills.registry import Backfill

runner = CliRunner()


def test_list_json_prints_the_catalogue_as_one_line() -> None:
    result = runner.invoke(cli.app, ["list", "--json"])

    assert result.exit_code == 0
    lines = result.stdout.strip().splitlines()
    assert len(lines) == 1
    catalogue = json.loads(lines[0])
    assert {
        "name": "note-word-count",
        "description": "Stamp word_count onto every stored note, computed from its body.",
    } in catalogue["backfills"]
    assert all(set(entry) == {"name", "description"} for entry in catalogue["backfills"])


def test_list_prints_names_and_descriptions() -> None:
    result = runner.invoke(cli.app, ["list"])

    assert result.exit_code == 0
    assert "note-word-count" in result.stdout
    assert "Stamp word_count" in result.stdout


def test_run_unknown_backfill_exits_non_zero() -> None:
    result = runner.invoke(cli.app, ["run", "does-not-exist"])

    assert result.exit_code != 0
    assert "Unknown backfill" in result.output


def test_run_passes_environment_apply_and_organization(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []

    def record(**kwargs: object) -> None:
        calls.append(kwargs)

    monkeypatch.setenv("FEATURE_ENVIRONMENT", "dev")
    monkeypatch.setattr(cli, "get", lambda name: Backfill(name=name, description="A test backfill.", run=record))

    result = runner.invoke(cli.app, ["run", "known", "--apply", "--organization-id", "org_1"])

    assert result.exit_code == 0
    assert calls == [{"environment": "dev", "apply": True, "organization_id": "org_1"}]
    assert "environment: dev (apply)" in result.stdout


def test_run_defaults_to_a_dry_run(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []

    def record(**kwargs: object) -> None:
        calls.append(kwargs)

    monkeypatch.setenv("FEATURE_ENVIRONMENT", "")
    monkeypatch.setattr(cli, "get", lambda name: Backfill(name=name, description="A test backfill.", run=record))

    result = runner.invoke(cli.app, ["run", "known"])

    assert result.exit_code == 0
    assert calls == [{"environment": "", "apply": False, "organization_id": None}]
    assert "environment: production (dry-run)" in result.stdout
