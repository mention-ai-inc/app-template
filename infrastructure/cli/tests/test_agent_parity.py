from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

HELPER = Path(__file__).resolve().parents[1] / "_helpers" / "agent_parity.py"


def write_json(path: Path, value: dict[str, list[str]]) -> None:
    path.write_text(json.dumps(value))


def run(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    helper = root / "infrastructure" / "cli" / "_helpers" / "agent_parity.py"
    return subprocess.run(["python3", "-I", str(helper), *arguments], text=True, capture_output=True)


@pytest.fixture
def root(tmp_path: Path) -> Path:
    helper = tmp_path / "infrastructure" / "cli" / "_helpers" / "agent_parity.py"
    helper.parent.mkdir(parents=True)
    shutil.copy(HELPER, helper)
    rules = tmp_path / ".agents" / "rules"
    rules.mkdir(parents=True)
    (rules / "base.md").write_text("## Base\n")
    (rules / "python-only.md").write_text("## Python\n")
    (rules / "deployment-plan.md").write_text("## Deploy\n")
    write_json(tmp_path / ".agents" / "rules.json", {"base": ["**/*.py"]})
    write_json(tmp_path / ".agents" / "rules.language.json", {"python-only": ["services/**/*.py"]})
    write_json(tmp_path / ".agents" / "rules.provider.json", {"deployment-plan": []})
    skill = tmp_path / ".agents" / "skills" / "build-feature"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: build-feature\ndescription: Build a feature.\n---\n")
    (skill / "LANGUAGE.md").write_text("Python paths.\n")
    return tmp_path


def test_sync_merges_language_and_provider_manifests(root: Path) -> None:
    result = run(root, "--sync")
    assert result.returncode == 0, result.stderr

    language_rule = (root / ".claude" / "rules" / "python-only.md").read_text()
    assert language_rule == '---\npaths:\n  - "services/**/*.py"\n---\n\n## Python\n'
    provider_rule = (root / ".cursor" / "rules" / "deployment-plan.mdc").read_text()
    assert provider_rule == "---\nalwaysApply: true\n---\n\n## Deploy\n"
    assert (root / ".claude" / "skills" / "build-feature" / "LANGUAGE.md").read_text() == "Python paths.\n"
    assert (root / ".cursor" / "skills" / "build-feature" / "LANGUAGE.md").read_text() == "Python paths.\n"
    assert (root / "CLAUDE.md").read_text() == "@AGENTS.md\n"
    assert run(root).returncode == 0


def test_language_manifest_may_not_redefine_a_base_rule(root: Path) -> None:
    write_json(root / ".agents" / "rules.language.json", {"base": ["services/**/*.py"], "python-only": []})

    result = run(root, "--sync")

    assert result.returncode == 1
    assert "rules.language.json" in result.stderr
    assert "['base']" in result.stderr


def test_provider_manifest_may_not_redefine_a_language_rule(root: Path) -> None:
    write_json(root / ".agents" / "rules.provider.json", {"deployment-plan": [], "python-only": []})

    result = run(root, "--sync")

    assert result.returncode == 1
    assert "rules.provider.json" in result.stderr
    assert "['python-only']" in result.stderr


def test_rule_file_without_a_manifest_entry_is_an_error(root: Path) -> None:
    (root / ".agents" / "rules" / "orphan.md").write_text("## Orphan\n")

    result = run(root, "--sync")

    assert result.returncode == 1
    assert "extra=['orphan']" in result.stderr
