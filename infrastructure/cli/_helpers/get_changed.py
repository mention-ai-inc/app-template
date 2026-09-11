import json
from argparse import ArgumentParser
from typing import TypedDict

import git

LAST_DEPLOYED_TAG = "demo-deployed"


class Diff(TypedDict):
    services: list[str]
    library: bool
    web: bool
    mcp: bool
    admin: bool


def resolve_baseline(*, repo: git.Repo, compare_to: str) -> str:
    if compare_to == "previous":
        return "HEAD~1"
    if compare_to == "main":
        return "origin/main"
    if compare_to == "last-deployed":
        if any(tag.name == LAST_DEPLOYED_TAG for tag in repo.tags):
            return LAST_DEPLOYED_TAG
        return "HEAD~1"
    raise ValueError("Invalid comparison")


def changed_paths(*, repo: git.Repo, baseline: str, include_uncommitted: bool) -> set[str]:
    """Every path that differs from the baseline, optionally counting work nobody has committed.

    `index.diff` compares the index alone, so a working tree full of edits that were never staged
    reads as no change at all — which is how a local run selects nothing to test and says so as if
    it were good news. Diffing the baseline commit against the working tree covers staged and
    unstaged edits alike, and untracked files are folded in because a brand new test file is a
    change too.

    Deployment target selection deliberately does not ask for this: what ships should be decided by
    what is committed, not by whatever happens to be lying around in the tree.
    """
    if not include_uncommitted:
        staged: list[git.Diff] = list(repo.index.diff(baseline))
        return _paths_of(diffs=staged)

    uncommitted: list[git.Diff] = list(repo.commit(baseline).diff(None))
    return _paths_of(diffs=uncommitted) | set(repo.untracked_files)


def changed_services(*, paths: set[str]) -> list[str]:
    return sorted({path.split("/")[1] for path in paths if path.startswith("services/")})


def _paths_of(*, diffs: list[git.Diff]) -> set[str]:
    return {path for item in diffs for path in (item.a_path, item.b_path) if path is not None}


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("--compare-to", type=str)
    parser.add_argument("--include-uncommitted", action="store_true")
    args = parser.parse_args()

    repo = git.Repo(search_parent_directories=True)
    paths = changed_paths(
        repo=repo,
        baseline=resolve_baseline(repo=repo, compare_to=args.compare_to),
        include_uncommitted=args.include_uncommitted,
    )

    diff: Diff = {
        "services": changed_services(paths=paths),
        "library": any(path.startswith("library/") for path in paths),
        "web": any(path.startswith("apps/web/") for path in paths),
        "mcp": any(path.startswith("apps/mcp/") for path in paths),
        "admin": any(path.startswith("admin/") for path in paths),
    }
    print(json.dumps(diff))


if __name__ == "__main__":
    main()
