import hashlib
import json
import re
import urllib.request
from importlib.resources import files
from pathlib import Path
from typing import Any

from mention_template import __version__, setup

CLOUDS = ("aws", "gcp", "azure")
REPOSITORY = "https://github.com/mention-ai-inc/app-template"
MAX_DOWNLOAD = 64 * 1024 * 1024


def manifest() -> dict[str, Any]:
    resource = files("mention_template").joinpath("templates.json")
    if not resource.is_file():
        raise ValueError(
            "This development build has no release snapshots. Use a published beta or m build-template-release."
        )
    value = json.loads(resource.read_text())
    if (
        value.get("version") != __version__
        or value.get("repository") != REPOSITORY
        or set(value.get("clouds", {})) != set(CLOUDS)
    ):
        raise ValueError("The bundled template manifest does not match this launcher")
    for cloud, snapshot in value["clouds"].items():
        expected_url = f"{REPOSITORY}/releases/download/template-v{__version__}/{cloud}.tar.gz"
        if (
            snapshot.get("url") != expected_url
            or not re.fullmatch(r"[0-9a-f]{64}", snapshot.get("sha256", ""))
            or not re.fullmatch(r"[0-9a-f]{40}", snapshot.get("revision", ""))
        ):
            raise ValueError(f"Invalid release snapshot for {cloud}")
    return value


def download(snapshot: dict[str, str]) -> bytes:
    request = urllib.request.Request(snapshot["url"], headers={"User-Agent": f"mention-template/{__version__}"})
    with urllib.request.urlopen(request, timeout=30) as response:
        archive = response.read(MAX_DOWNLOAD + 1)
    if len(archive) > MAX_DOWNLOAD:
        raise ValueError("The template download exceeds the supported size")
    if hashlib.sha256(archive).hexdigest() != snapshot["sha256"]:
        raise ValueError("Template checksum verification failed. No project was created.")
    return archive


def create(cloud: str, destination: Path) -> None:
    if destination.is_symlink() or (destination.exists() and (not destination.is_dir() or any(destination.iterdir()))):
        raise ValueError("Destination must be absent or empty, and not a symlink")
    if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", destination.name):
        raise ValueError(
            "The destination name must start with a lowercase letter and use letters, digits, and single hyphens"
        )
    value = manifest()
    snapshot = value["clouds"][cloud]
    print(f"Downloading {cloud} template {__version__} at {snapshot['revision']}...", flush=True)
    archive = download(snapshot)
    setup.initialize_project(archive, value["repository"], snapshot["revision"], cloud, destination)
