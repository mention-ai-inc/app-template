import argparse
import fnmatch
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from mention_template import setup
from mention_template.templates import CLOUDS, LANGUAGES

MAIN = "main"
LEAF_ONLY: dict[str, tuple[str, ...]] = {"python": (), "ts": ("library/providers/",)}
SLOT_READMES = (
    "library/README.md",
    "library/providers/README.md",
    "services/README.md",
    "backfills/README.md",
    "control-plane/providers/README.md",
    "infrastructure/cli/language/README.md",
    "infrastructure/cli/provider/README.md",
    "infrastructure/docker/services/README.md",
    "infrastructure/docker/backfills/README.md",
    "infrastructure/docker/provider/README.md",
)
LANGUAGE_OWNED = (
    "library/",
    "services/",
    "backfills/",
    "infrastructure/cli/language/",
    "infrastructure/docker/services/",
    "infrastructure/docker/backfills/",
    ".agents/rules.language.json",
    ".agents/rules/",
    ".agents/skills/*/LANGUAGE.md",
    ".claude/rules/",
    ".claude/skills/*/LANGUAGE.md",
    ".cursor/rules/",
    ".cursor/skills/*/LANGUAGE.md",
    "docs/*.language.md",
)
CLOUD_OWNED = (
    "infrastructure/terraform/",
    "infrastructure/cli/provider/",
    "infrastructure/docker/provider/",
    "control-plane/providers/",
    ".github/workflows/",
    ".agents/rules.provider.json",
    ".agents/rules/",
    ".agents/skills/",
    ".claude/rules/",
    ".claude/skills/",
    ".cursor/rules/",
    ".cursor/skills/",
    "docs/",
    "PROVIDER.md",
    ".*ignore",
)
PROVIDER_MANIFEST = "infrastructure/cli/provider/project.json"
LANGUAGE_MANIFEST = "infrastructure/cli/language/project.json"
NON_ADDITIVE_FILTER = "--diff-filter=CDMRTUXB"


class BranchError(ValueError):
    pass


@dataclass(frozen=True)
class Topology:
    languages: tuple[str, ...] = LANGUAGES
    clouds: tuple[str, ...] = CLOUDS

    @property
    def language_branches(self) -> list[str]:
        return [f"lang/{language}" for language in self.languages]

    @property
    def cloud_branches(self) -> list[str]:
        return [f"cloud/{cloud}" for cloud in self.clouds]

    @property
    def leaves(self) -> list[tuple[str, str, str]]:
        return [(language, cloud, f"{language}/{cloud}") for language in self.languages for cloud in self.clouds]

    @property
    def leaf_branches(self) -> list[str]:
        return [leaf for _, _, leaf in self.leaves]

    @property
    def branches(self) -> list[str]:
        return [*self.language_branches, *self.cloud_branches, *self.leaf_branches]


@dataclass
class Report:
    findings: dict[str, list[str]] = field(default_factory=dict)
    additions: dict[str, int] = field(default_factory=dict)

    def add(self, branch: str, message: str) -> None:
        self.findings.setdefault(branch, []).append(message)

    @property
    def ok(self) -> bool:
        return not self.findings


def owned(path: str, patterns: tuple[str, ...]) -> bool:
    return any(matches(path, pattern) for pattern in patterns)


def matches(path: str, pattern: str) -> bool:
    if pattern.endswith("/"):
        return path.startswith(pattern)
    path_parts = path.split("/")
    pattern_parts = pattern.split("/")
    if len(path_parts) != len(pattern_parts):
        return False
    return all(fnmatch.fnmatchcase(part, expected) for part, expected in zip(path_parts, pattern_parts))


class Repository:
    def __init__(self, root: Path, stand_ins: dict[str, str] | None = None) -> None:
        self.root = root
        self.stand_ins = stand_ins or {}

    def git(self, *arguments: str) -> str:
        return setup.run(self.root, "git", *arguments, timeout=600)

    def exists(self, branch: str) -> bool:
        return self.resolve(branch) is not None

    def exists_locally(self, branch: str) -> bool:
        return self.resolve(branch, local_only=True) is not None

    def revision(self, branch: str) -> str:
        revision = self.resolve(branch)
        if revision is None:
            raise BranchError(f"Branch {branch} is missing; fetch it before checking the topology")
        return revision

    def resolve(self, branch: str, *, local_only: bool = False) -> str | None:
        if branch in self.stand_ins:
            return self.stand_ins[branch]
        references = [f"refs/heads/{branch}"]
        if not local_only:
            references.append(f"refs/remotes/origin/{branch}")
        for reference in references:
            try:
                return self.git("rev-parse", "--verify", "--quiet", f"{reference}^{{commit}}")
            except ValueError:
                continue
        return None

    def merge_base(self, first: str, second: str) -> str:
        return self.git("merge-base", first, second)

    def contains(self, revision: str, ancestor: str) -> bool:
        try:
            self.git("merge-base", "--is-ancestor", ancestor, revision)
        except ValueError:
            return False
        return True

    def files(self, revision: str) -> set[str]:
        return set(self.git("ls-tree", "-r", "--name-only", revision).splitlines())

    def added(self, base: str, revision: str) -> set[str]:
        return set(self.git("diff", "--name-only", "--diff-filter=A", base, revision).splitlines())

    def non_additive(self, base: str, revision: str) -> set[str]:
        return set(self.git("diff", "--name-only", NON_ADDITIVE_FILTER, base, revision).splitlines())

    def read(self, revision: str, path: str) -> str:
        return self.git("show", f"{revision}:{path}")

    def current_branch(self) -> str:
        return self.git("branch", "--show-current")

    def dirty(self) -> bool:
        return bool(self.git("status", "--porcelain", "--untracked-files=no"))


class Checker:
    def __init__(self, repository: Repository, topology: Topology) -> None:
        self.repository = repository
        self.topology = topology
        self.report = Report()
        self.main = repository.revision(MAIN)
        self.main_files = repository.files(self.main)
        self.__revisions: dict[str, str] = {}
        self.__additions: dict[str, set[str]] = {}

    def check(self, *, strict: bool = False) -> Report:
        self.check_main()
        for branch in self.topology.branches:
            self.check_branch(branch, strict=strict)
        return self.report

    def check_main(self) -> None:
        for readme in SLOT_READMES:
            if readme not in self.main_files:
                self.report.add(MAIN, f"slot README {readme} is missing")

    def check_branch(self, branch: str, *, strict: bool = False) -> None:
        self.__check_additive(branch)
        if branch in self.topology.language_branches:
            self.__check_ownership(branch, LANGUAGE_OWNED, "a language branch")
            for cloud_branch in self.topology.cloud_branches:
                self.__check_disjoint(branch, cloud_branch)
        elif branch in self.topology.cloud_branches:
            self.__check_ownership(branch, CLOUD_OWNED, "a cloud branch")
        else:
            self.__check_leaf(branch)
        if strict:
            self.__check_strict(branch)

    def revision(self, branch: str) -> str:
        if branch not in self.__revisions:
            self.__revisions[branch] = self.repository.revision(branch)
        return self.__revisions[branch]

    def additions(self, branch: str) -> set[str]:
        if branch not in self.__additions:
            revision = self.revision(branch)
            base = self.repository.merge_base(self.main, revision)
            self.__additions[branch] = self.repository.added(base, revision)
            self.report.additions[branch] = len(self.__additions[branch])
        return self.__additions[branch]

    def __check_additive(self, branch: str) -> None:
        revision = self.revision(branch)
        base = self.repository.merge_base(self.main, revision)
        for path in sorted(self.repository.non_additive(base, revision)):
            self.report.add(branch, f"changes {path}, a file main also has")
        for path in sorted(self.additions(branch) & self.main_files):
            self.report.add(branch, f"adds {path}, which main has since added too")

    def __check_ownership(self, branch: str, patterns: tuple[str, ...], owner: str) -> None:
        for path in sorted(self.additions(branch)):
            if not owned(path, patterns):
                self.report.add(branch, f"adds {path}, which {owner} does not own")

    def __check_disjoint(self, language_branch: str, cloud_branch: str) -> None:
        for path in sorted(self.additions(language_branch) & self.additions(cloud_branch)):
            self.report.add(language_branch, f"adds {path}, which {cloud_branch} also adds")

    def __check_leaf(self, leaf: str) -> None:
        language, cloud = leaf.split("/")
        language_branch, cloud_branch = f"lang/{language}", f"cloud/{cloud}"
        expected = self.additions(language_branch) | self.additions(cloud_branch)
        actual = self.additions(leaf)
        for path in sorted(expected - actual):
            self.report.add(leaf, f"is missing {path}; run m sync-branches")
        leaf_only = tuple(f"{prefix}{cloud}/" for prefix in LEAF_ONLY.get(language, ()))
        for path in sorted(actual - expected):
            if not leaf_only or not owned(path, leaf_only):
                self.report.add(leaf, f"adds {path}, which neither {language_branch} nor {cloud_branch} adds")
        self.__check_leaf_manifests(leaf, language, cloud)

    def __check_leaf_manifests(self, leaf: str, language: str, cloud: str) -> None:
        revision = self.revision(leaf)
        files = self.repository.files(revision)
        providers = sorted(
            path.split("/")[2] for path in files if matches(path, "control-plane/providers/*/pyproject.toml")
        )
        if providers != [cloud]:
            self.report.add(leaf, f"must hold exactly one Python provider named {cloud}, found {providers or 'none'}")
        self.__check_manifest(leaf, revision, files, PROVIDER_MANIFEST, "cloud", cloud)
        self.__check_manifest(leaf, revision, files, LANGUAGE_MANIFEST, "language", language)

    def __check_manifest(self, leaf: str, revision: str, files: set[str], path: str, key: str, expected: str) -> None:
        if path not in files:
            self.report.add(leaf, f"is missing {path}")
            return
        try:
            value = json.loads(self.repository.read(revision, path)).get(key)
        except (ValueError, AttributeError):
            value = None
        if value != expected:
            self.report.add(leaf, f"{path} names {key} {value!r}, expected {expected!r}")

    def __check_strict(self, branch: str) -> None:
        revision = self.revision(branch)
        if not self.repository.contains(revision, self.main):
            self.report.add(branch, "does not contain main; run m sync-branches")
        if branch in self.topology.leaf_branches:
            language, cloud = branch.split("/")
            for parent in (f"lang/{language}", f"cloud/{cloud}"):
                if not self.repository.contains(revision, self.revision(parent)):
                    self.report.add(branch, f"does not contain {parent}; run m sync-branches")


def refuse_in_product(root: Path) -> None:
    if (root / setup.CONFIG).exists():
        raise BranchError("Branch maintenance applies to the template repository, not a generated product")


def require_branches(repository: Repository, topology: Topology, *, local_only: bool) -> None:
    missing = [
        branch
        for branch in (MAIN, *topology.branches)
        if not (repository.exists_locally(branch) if local_only else repository.exists(branch))
    ]
    if missing:
        where = "as local branches" if local_only else "locally or on origin"
        raise BranchError(f"Missing branches ({where}): {', '.join(missing)}")


def check(root: Path, *, strict: bool = False, stand_in: str | None = None, topology: Topology = Topology()) -> Report:
    refuse_in_product(root)
    repository = Repository(root)
    if stand_in is not None:
        if stand_in in (MAIN, *topology.branches):
            repository = Repository(root, {stand_in: repository.git("rev-parse", "HEAD")})
        else:
            print(f"HEAD does not stand in for a topology branch ({stand_in}); checking branches as they are.")
    require_branches(repository, topology, local_only=False)
    return Checker(repository, topology).check(strict=strict)


def sync(root: Path, *, topology: Topology = Topology()) -> tuple[Report, dict[str, str]]:
    refuse_in_product(root)
    repository = Repository(root)
    origin = repository.current_branch()
    if not origin:
        raise BranchError("Switch to a branch before synchronizing; HEAD is detached")
    if repository.dirty():
        raise BranchError("Commit or stash changes before synchronizing")
    require_branches(repository, topology, local_only=True)
    outcomes: dict[str, str] = {}
    checker = Checker(repository, topology)
    parents = {
        **{branch: [MAIN] for branch in (*topology.language_branches, *topology.cloud_branches)},
        **{leaf: [MAIN, f"lang/{language}", f"cloud/{cloud}"] for language, cloud, leaf in topology.leaves},
    }
    try:
        for branch, branch_parents in parents.items():
            outcomes[branch] = merge_into(repository, branch, branch_parents)
            checker.check_branch(branch)
            if checker.report.findings.get(branch):
                return checker.report, outcomes
    finally:
        repository.git("switch", origin)
    return Checker(repository, topology).check(strict=True), outcomes


def merge_into(repository: Repository, branch: str, parents: list[str]) -> str:
    before = repository.revision(branch)
    repository.git("switch", branch)
    for parent in parents:
        try:
            repository.git("merge", "--no-edit", parent)
        except ValueError as error:
            try:
                repository.git("merge", "--abort")
            except ValueError:
                pass
            raise BranchError(f"Merging {parent} into {branch} conflicted; the merge was aborted: {error}") from error
    after = repository.revision(branch)
    return "up to date" if before == after else f"merged {before[:7]}..{after[:7]}"


def table(report: Report, outcomes: dict[str, str] | None, topology: Topology) -> str:
    rows = [("branch", "additions", "sync", "result")]
    for branch in (MAIN, *topology.branches):
        findings = report.findings.get(branch, [])
        additions = "" if branch == MAIN else str(report.additions.get(branch, ""))
        synced = "" if outcomes is None else outcomes.get(branch, "")
        result = "ok" if not findings else f"{len(findings)} problem{'s' if len(findings) != 1 else ''}"
        rows.append((branch, additions, synced, result))
    widths = [max(len(row[column]) for row in rows) for column in range(4)]
    lines = ["  ".join(cell.ljust(width) for cell, width in zip(row, widths)).rstrip() for row in rows]
    for branch, findings in report.findings.items():
        lines.extend(f"{branch}: {finding}" for finding in findings)
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check or synchronize the template's branch topology.")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument(
        "--sync", action="store_true", help="merge main into every branch and the parents into every leaf"
    )
    parser.add_argument("--strict", action="store_true", help="also require every branch to contain main")
    parser.add_argument("--as", dest="stand_in", help="treat HEAD as the tip of this branch (check only)")
    args = parser.parse_args()
    root = args.root.resolve()
    topology = Topology()
    try:
        if args.sync:
            if args.stand_in:
                raise BranchError("--as applies to checks only")
            report, outcomes = sync(root, topology=topology)
        else:
            report, outcomes = check(root, strict=args.strict, stand_in=args.stand_in, topology=topology), None
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"Branch error: {error}", file=sys.stderr)
        return 1
    print(table(report, outcomes, topology))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
