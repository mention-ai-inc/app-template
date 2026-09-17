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
from mention_template.templates import CLOUDS, REPOSITORY


def cloud_revision(root: Path, cloud: str) -> str:
    for reference in (f"refs/heads/cloud/{cloud}", f"refs/remotes/origin/cloud/{cloud}"):
        try:
            return setup.run(root, "git", "rev-parse", "--verify", f"{reference}^{{commit}}")
        except ValueError:
            continue
    raise ValueError(f"Fetch cloud/{cloud} before building a release")


def release_manifest(root: Path, output: Path) -> dict[str, Any]:
    base = setup.run(root, "git", "rev-parse", "HEAD")
    snapshots: dict[str, dict[str, str]] = {}
    for cloud in CLOUDS:
        revision = cloud_revision(root, cloud)
        setup.run(root, "git", "merge-base", "--is-ancestor", base, revision)
        if setup.run(root, "git", "diff", "--name-only", "--diff-filter=CDMRTUXB", base, revision):
            raise ValueError(f"cloud/{cloud} modifies shared files; merge the shared release commit outward first")
        archive = subprocess.run(
            ["git", "archive", "--format=tar.gz", revision], cwd=root, check=True, capture_output=True
        ).stdout
        with tempfile.TemporaryDirectory(prefix="mention-release-check-") as temporary:
            product = Path(temporary) / "release-check"
            setup.initialize_project(archive, REPOSITORY, revision, cloud, product)
            if not (product / ".agents/skills/start-project/SKILL.md").is_file():
                raise ValueError(f"cloud/{cloud} is missing onboarding guidance")
            if not (product / "tools/mention-template/src/mention_template/setup.py").is_file():
                raise ValueError(f"cloud/{cloud} is missing the shared setup engine")
        (output / f"{cloud}.tar.gz").write_bytes(archive)
        snapshots[cloud] = {
            "revision": revision,
            "sha256": hashlib.sha256(archive).hexdigest(),
            "url": f"{REPOSITORY}/releases/download/template-v{__version__}/{cloud}.tar.gz",
        }
    return {"version": __version__, "repository": REPOSITORY, "base_revision": base, "clouds": snapshots}


def build(root: Path, output: Path) -> None:
    if (root / "project.json").exists():
        raise ValueError("Template releases can only be built from the template repository")
    if setup.run(root, "git", "status", "--porcelain"):
        raise ValueError("Commit changes and synchronize cloud branches before building a release")
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
    parser = argparse.ArgumentParser(description="Build the launcher and its three pinned cloud snapshots.")
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
