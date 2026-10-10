import argparse
import hashlib
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import Any

from mention_template import __version__, setup
from mention_template.branches import Repository, Topology
from mention_template.templates import CLOUDS, LANGUAGES, REPOSITORY, leaf, snapshot_url


def release_manifest(root: Path, output: Path) -> dict[str, Any]:
    repository = Repository(root)
    base = repository.git("rev-parse", "HEAD")
    snapshots: dict[str, dict[str, str]] = {}
    for language, cloud, branch in Topology().leaves:
        revision = repository.revision(branch)
        if not repository.contains(revision, base):
            raise ValueError(f"{branch} does not contain the release commit; run m sync-branches first")
        if repository.non_additive(base, revision):
            raise ValueError(f"{branch} modifies shared files; run m check-branches")
        archive = subprocess.run(
            ["git", "archive", "--format=tar.gz", revision], cwd=root, check=True, capture_output=True
        ).stdout
        with tempfile.TemporaryDirectory(prefix="mention-release-check-") as temporary:
            product = Path(temporary) / "release-check"
            setup.initialize_project(archive, REPOSITORY, revision, language, cloud, product)
            if not (product / ".agents/skills/start-project/SKILL.md").is_file():
                raise ValueError(f"{branch} is missing onboarding guidance")
            if not (product / "tools/mention-template/src/mention_template/setup.py").is_file():
                raise ValueError(f"{branch} is missing the shared setup engine")
        name = leaf(language, cloud)
        (output / f"{name}.tar.gz").write_bytes(archive)
        snapshots[name] = {
            "revision": revision,
            "sha256": hashlib.sha256(archive).hexdigest(),
            "url": snapshot_url(name),
        }
    return {
        "version": __version__,
        "repository": REPOSITORY,
        "base_revision": base,
        "languages": list(LANGUAGES),
        "clouds": list(CLOUDS),
        "snapshots": snapshots,
    }


def build(root: Path, output: Path) -> None:
    if (root / "project.json").exists():
        raise ValueError("Template releases can only be built from the template repository")
    if setup.run(root, "git", "status", "--porcelain"):
        raise ValueError("Commit changes and synchronize the branches before building a release")
    if output.exists():
        raise ValueError("Release output already exists; choose a new --output directory")
    package = root / "tools/mention-template"
    metadata = tomllib.loads((package / "pyproject.toml").read_text())
    if metadata["project"]["version"] != __version__:
        raise ValueError("Package metadata and launcher version differ")
    if (root / "LICENSE").read_bytes() != (package / "LICENSE").read_bytes():
        raise ValueError("The package license must match the template license")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mention-release-", dir=output.parent) as temporary:
        staging = Path(temporary)
        artifacts = staging / "artifacts"
        artifacts.mkdir()
        manifest = release_manifest(root, artifacts)
        setup.save(artifacts / "templates.json", manifest)
        source = staging / "package"
        source.mkdir()
        for name in ("pyproject.toml", "README.md", "LICENSE"):
            shutil.copy2(package / name, source / name)
        shutil.copytree(package / "src", source / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        setup.save(source / "src/mention_template/templates.json", manifest)
        subprocess.run(["uv", "build", "--no-sources", "--out-dir", str(artifacts), str(source)], check=True, cwd=root)
        artifacts.rename(output)
    print(f"Release {__version__} built in {output}. Nothing has been published.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the launcher and one pinned snapshot per language-and-cloud leaf."
    )
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        build(root, (args.output or root / "dist/template-release").absolute())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"Release error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
