import json
import subprocess
import sys
from pathlib import Path

import pytest
from mention_template import branches
from mention_template.branches import BranchError, Topology

TOPOLOGY = Topology(languages=("python",), clouds=("gcp",))
GUIDANCE = (
    ".agents/rules.language.json",
    ".agents/skills/build-feature/LANGUAGE.md",
    ".claude/skills/build-feature/LANGUAGE.md",
    "docs/add-service.language.md",
    "backfills/pyproject.toml",
    "infrastructure/docker/services/Dockerfile",
    ".agents/rules.provider.json",
    ".agents/skills/deploy-branch/SKILL.md",
    ".cursor/skills/deploy-branch/SKILL.md",
    ".github/workflows/deployment.yaml",
    "docs/bootstrap.md",
    "infrastructure/docker/provider/build",
)


def git(root: Path, *arguments: str) -> str:
    result = subprocess.run(["git", *arguments], cwd=root, check=True, text=True, capture_output=True)
    return result.stdout.strip()


def commit(root: Path, message: str, files: dict[str, str]) -> None:
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    git(root, "add", "--all")
    git(root, "commit", "--quiet", "--message", message)


def on_branch(root: Path, branch: str, message: str, files: dict[str, str]) -> None:
    git(root, "switch", "--quiet", branch)
    commit(root, message, files)
    git(root, "switch", "--quiet", "main")


@pytest.fixture
def repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for variable in ("GIT_AUTHOR_NAME", "GIT_COMMITTER_NAME"):
        monkeypatch.setenv(variable, "Template Tests")
    for variable in ("GIT_AUTHOR_EMAIL", "GIT_COMMITTER_EMAIL"):
        monkeypatch.setenv(variable, "tests@example.org")
    root = tmp_path / "template"
    root.mkdir()
    git(root, "init", "--quiet", "--initial-branch=main")
    commit(
        root,
        "Base",
        {
            "README.md": "Acme\n",
            "pyproject.toml": "[tool]\n",
            "infrastructure/cli/Makefile": "all:\n",
            **{readme: f"# {readme}\n" for readme in branches.SLOT_READMES},
        },
    )
    git(root, "branch", "lang/python")
    git(root, "branch", "cloud/gcp")
    on_branch(
        root,
        "lang/python",
        "Add the Python backend",
        {
            "library/library/__init__.py": "",
            "services/notes/pyproject.toml": "[project]\nname = 'notes'\n",
            "infrastructure/cli/language/project.json": json.dumps({"language": "python"}),
            ".agents/rules/python-service-tests.md": "rule\n",
        },
    )
    on_branch(
        root,
        "cloud/gcp",
        "Add the GCP provider",
        {
            "control-plane/providers/gcp/pyproject.toml": "[project]\nname = 'control-plane-provider-gcp'\n",
            "infrastructure/cli/provider/project.json": json.dumps({"cloud": "gcp", "fields": []}),
            "infrastructure/terraform/main.tf": 'provider "google" {}\n',
            ".agents/rules/deployment-plan.md": "rule\n",
            "PROVIDER.md": "GCP\n",
            ".gcloudignore": "node_modules\n",
        },
    )
    git(root, "switch", "--quiet", "--create", "python/gcp", "main")
    git(root, "merge", "--quiet", "--no-edit", "lang/python")
    git(root, "merge", "--quiet", "--no-edit", "cloud/gcp")
    git(root, "switch", "--quiet", "main")
    return root


def findings(root: Path, *, strict: bool = False, stand_in: str | None = None) -> dict[str, list[str]]:
    return branches.check(root, strict=strict, stand_in=stand_in, topology=TOPOLOGY).findings


def test_consistent_topology_passes(repository: Path) -> None:
    report = branches.check(repository, strict=True, topology=TOPOLOGY)
    assert report.ok
    assert report.additions == {"lang/python": 4, "cloud/gcp": 6, "python/gcp": 10}


def test_sync_merges_outward_and_is_idempotent(repository: Path) -> None:
    report, outcomes = branches.sync(repository, topology=TOPOLOGY)
    assert report.ok
    assert set(outcomes.values()) == {"up to date"}
    commit(repository, "Base change", {"docs/new.md": "shared\n"})
    assert findings(repository) == {}
    assert findings(repository, strict=True) == {
        "lang/python": ["does not contain main; run m sync-branches"],
        "cloud/gcp": ["does not contain main; run m sync-branches"],
        "python/gcp": ["does not contain main; run m sync-branches"],
    }
    report, outcomes = branches.sync(repository, topology=TOPOLOGY)
    assert report.ok
    assert all(outcome.startswith("merged ") for outcome in outcomes.values())
    assert git(repository, "branch", "--show-current") == "main"
    assert git(repository, "ls-tree", "--name-only", "python/gcp", "docs/") == "docs/new.md"
    assert findings(repository, strict=True) == {}
    _, outcomes = branches.sync(repository, topology=TOPOLOGY)
    assert set(outcomes.values()) == {"up to date"}


def test_sync_merges_new_parent_files_into_the_leaf(repository: Path) -> None:
    on_branch(repository, "lang/python", "Add a service", {"services/billing/pyproject.toml": "[project]\n"})
    on_branch(repository, "cloud/gcp", "Add a module", {"infrastructure/terraform/modules/cache.tf": ""})
    assert findings(repository) == {
        "python/gcp": [
            "is missing infrastructure/terraform/modules/cache.tf; run m sync-branches",
            "is missing services/billing/pyproject.toml; run m sync-branches",
        ]
    }
    report, _ = branches.sync(repository, topology=TOPOLOGY)
    assert report.ok


def test_branch_editing_a_main_file_is_reported(repository: Path) -> None:
    on_branch(repository, "cloud/gcp", "Edit base", {"README.md": "GCP flavoured\n"})
    assert findings(repository)["cloud/gcp"] == ["changes README.md, a file main also has"]


def test_branch_file_that_main_later_adds_is_reported(repository: Path) -> None:
    commit(repository, "Base adds the same file", {"PROVIDER.md": "base\n"})
    assert findings(repository)["cloud/gcp"] == ["adds PROVIDER.md, which main has since added too"]


def test_language_and_cloud_additions_must_be_disjoint(repository: Path) -> None:
    on_branch(repository, "lang/python", "Shared rule", {".agents/rules/shared.md": "python\n"})
    on_branch(repository, "cloud/gcp", "Shared rule", {".agents/rules/shared.md": "gcp\n"})
    assert findings(repository)["lang/python"] == ["adds .agents/rules/shared.md, which cloud/gcp also adds"]


def test_ownership_is_enforced_per_axis(repository: Path) -> None:
    on_branch(repository, "lang/python", "Stray app file", {"apps/web/src/python.ts": ""})
    on_branch(repository, "cloud/gcp", "Stray kernel file", {"library/library/gcp.py": ""})
    report = findings(repository)
    assert report["lang/python"] == ["adds apps/web/src/python.ts, which a language branch does not own"]
    assert report["cloud/gcp"] == ["adds library/library/gcp.py, which a cloud branch does not own"]


def test_language_may_add_guidance_and_cloud_may_add_docs(repository: Path) -> None:
    on_branch(
        repository,
        "lang/python",
        "Guidance",
        {
            ".agents/rules.language.json": "{}",
            ".agents/skills/build-feature/LANGUAGE.md": "",
            ".claude/skills/build-feature/LANGUAGE.md": "",
            "docs/add-service.language.md": "",
            "backfills/pyproject.toml": "",
            "infrastructure/docker/services/Dockerfile": "",
        },
    )
    on_branch(
        repository,
        "cloud/gcp",
        "Guidance",
        {
            ".agents/rules.provider.json": "{}",
            ".agents/skills/deploy-branch/SKILL.md": "",
            ".cursor/skills/deploy-branch/SKILL.md": "",
            ".github/workflows/deployment.yaml": "",
            "docs/bootstrap.md": "",
            "infrastructure/docker/provider/build": "",
        },
    )
    assert findings(repository) == {
        "python/gcp": [f"is missing {path}; run m sync-branches" for path in sorted(GUIDANCE)]
    }


def test_leaf_may_not_add_its_own_files(repository: Path) -> None:
    on_branch(repository, "python/gcp", "Leaf only", {"library/providers/gcp/package.json": "{}"})
    assert findings(repository)["python/gcp"] == [
        "adds library/providers/gcp/package.json, which neither lang/python nor cloud/gcp adds"
    ]


def test_leaf_manifests_are_verified(repository: Path) -> None:
    on_branch(
        repository,
        "cloud/gcp",
        "Second provider and wrong cloud",
        {
            "control-plane/providers/aws/pyproject.toml": "[project]\n",
            "infrastructure/cli/provider/project.json": json.dumps({"cloud": "aws", "fields": []}),
        },
    )
    git(repository, "switch", "--quiet", "python/gcp")
    git(repository, "merge", "--quiet", "--no-edit", "cloud/gcp")
    git(repository, "switch", "--quiet", "main")
    assert findings(repository)["python/gcp"] == [
        "must hold exactly one Python provider named gcp, found ['aws', 'gcp']",
        "infrastructure/cli/provider/project.json names cloud 'aws', expected 'gcp'",
    ]


def test_missing_slot_readme_on_main_is_reported(repository: Path) -> None:
    git(repository, "rm", "--quiet", "services/README.md")
    git(repository, "commit", "--quiet", "--message", "Drop a slot README")
    assert findings(repository)["main"] == ["slot README services/README.md is missing"]


def test_missing_branches_are_refused(repository: Path) -> None:
    with pytest.raises(BranchError, match="Missing branches .*: lang/ts, cloud/aws, python/aws, ts/gcp, ts/aws"):
        branches.check(repository, topology=Topology(languages=("python", "ts"), clouds=("gcp", "aws")))


def test_generated_product_is_refused(repository: Path) -> None:
    (repository / "project.json").write_text("{}")
    with pytest.raises(BranchError, match="generated product"):
        branches.check(repository, topology=TOPOLOGY)
    with pytest.raises(BranchError, match="generated product"):
        branches.sync(repository, topology=TOPOLOGY)


def test_sync_refuses_dirty_tree_and_detached_head(repository: Path) -> None:
    (repository / "README.md").write_text("edited\n")
    with pytest.raises(BranchError, match="Commit or stash"):
        branches.sync(repository, topology=TOPOLOGY)
    git(repository, "checkout", "--quiet", "README.md")
    git(repository, "switch", "--quiet", "--detach", "main")
    with pytest.raises(BranchError, match="detached"):
        branches.sync(repository, topology=TOPOLOGY)
    git(repository, "switch", "--quiet", "main")
    git(repository, "branch", "--delete", "--force", "python/gcp")
    with pytest.raises(BranchError, match="Missing branches \\(as local branches\\): python/gcp"):
        branches.sync(repository, topology=TOPOLOGY)


def test_sync_conflict_aborts_and_returns_to_the_original_branch(repository: Path) -> None:
    commit(repository, "Base claims the file", {"infrastructure/terraform/main.tf": "base\n"})
    git(repository, "switch", "--quiet", "lang/python")
    with pytest.raises(BranchError, match="Merging main into cloud/gcp conflicted"):
        branches.sync(repository, topology=TOPOLOGY)
    assert git(repository, "branch", "--show-current") == "lang/python"
    assert not (repository / ".git/MERGE_HEAD").exists()
    assert git(repository, "status", "--porcelain") == ""
    assert git(repository, "merge-base", "--is-ancestor", "main", "lang/python") == ""


def test_sync_stops_at_the_first_structural_failure(repository: Path) -> None:
    on_branch(repository, "cloud/gcp", "Edit base", {"README.md": "GCP flavoured\n"})
    commit(repository, "Base change", {"docs/new.md": "shared\n"})
    report, outcomes = branches.sync(repository, topology=TOPOLOGY)
    assert report.findings == {"cloud/gcp": ["changes README.md, a file main also has"]}
    assert set(outcomes) == {"lang/python", "cloud/gcp"}
    assert git(repository, "branch", "--show-current") == "main"


def test_head_can_stand_in_for_a_branch(repository: Path) -> None:
    git(repository, "switch", "--quiet", "--detach", "cloud/gcp")
    commit(repository, "Proposed change", {"README.md": "GCP flavoured\n"})
    assert findings(repository) == {}
    assert findings(repository, stand_in="cloud/gcp")["cloud/gcp"] == ["changes README.md, a file main also has"]
    assert findings(repository, stand_in="feature/unrelated") == {}


@pytest.mark.parametrize(
    ("path", "pattern", "expected"),
    [
        ("library/library/x.py", "library/", True),
        ("library", "library/", False),
        (".agents/skills/build-feature/LANGUAGE.md", ".agents/skills/*/LANGUAGE.md", True),
        (".agents/skills/build-feature/SKILL.md", ".agents/skills/*/LANGUAGE.md", False),
        (".agents/skills/nested/deep/LANGUAGE.md", ".agents/skills/*/LANGUAGE.md", False),
        ("docs/add-service.language.md", "docs/*.language.md", True),
        ("docs/product/x.language.md", "docs/*.language.md", False),
        (".gcloudignore", ".*ignore", True),
        ("infrastructure/.gcloudignore", ".*ignore", False),
        ("PROVIDER.md", "PROVIDER.md", True),
    ],
)
def test_pattern_matching(path: str, pattern: str, expected: bool) -> None:
    assert branches.matches(path, pattern) is expected


def test_command_line_reports_errors(repository: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "mention_template.branches", "--root", str(repository)],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    assert "Branch error: Missing branches" in result.stderr
    result = subprocess.run(
        [sys.executable, "-m", "mention_template.branches", "--root", str(repository), "--sync", "--as", "main"],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    assert "--as applies to checks only" in result.stderr


def test_table_lists_every_branch(repository: Path) -> None:
    report = branches.check(repository, topology=TOPOLOGY)
    text = branches.table(report, {"lang/python": "up to date"}, TOPOLOGY)
    lines = text.splitlines()
    assert lines[0].split() == ["branch", "additions", "sync", "result"]
    assert [line.split()[0] for line in lines[1:]] == ["main", "lang/python", "cloud/gcp", "python/gcp"]
    assert lines[2].split() == ["lang/python", "4", "up", "to", "date", "ok"]
