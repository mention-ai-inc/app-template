#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import fnmatch
import hashlib
import html
import io
import json
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
CONFIG = "project.json"
STATE = ".project-template.json"
JOURNAL = ".project-setup-pending.json"
PROVIDER = "infrastructure/cli/provider/project.json"
SCOPES = [
    "AGENTS.md",
    "README.md",
    "package.json",
    "pyproject.toml",
    "pnpm-workspace.yaml",
    ".env.example",
    ".agents/**",
    "apps/**",
    "packages/**",
    "library/**",
    "services/**",
    "admin/**",
    "infrastructure/**",
    ".github/**",
    "docs/**",
]
EXCLUDED = [
    "**/node_modules/**",
    "**/.venv/**",
    "**/uv.lock",
    "**/routeTree.gen.ts",
    "infrastructure/cli/tests/**",
    "infrastructure/cli/_helpers/project_setup.py",
    PROVIDER,
]


def run(root: Path, *command: str, timeout: int = 60) -> str:
    result = subprocess.run(command, cwd=root, text=True, capture_output=True, timeout=timeout)
    if result.returncode:
        raise ValueError(f"{command[0]} failed: {result.stderr.strip() or result.stdout.strip()}")
    return result.stdout.strip()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value


def save(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def provider(root: Path) -> dict[str, Any]:
    path = root / PROVIDER
    if not path.exists():
        raise ValueError("No onboarding provider found. Use an updated cloud/gcp, cloud/aws, or cloud/azure snapshot.")
    return load(path)


def configuration(root: Path) -> dict[str, Any]:
    config = load(root / CONFIG)
    expected = {
        "version",
        "source",
        "cloud",
        "slug",
        "display_name",
        "domain",
        "github_repository",
        "cloud_values",
        "clerk",
        "surfaces",
        "monitoring",
    }
    if set(config) != expected or config["version"] != 1:
        raise ValueError("Unsupported project.json fields or version. Store credentials outside this file.")
    if config["cloud"] != provider(root)["cloud"]:
        raise ValueError("The configured cloud does not match the installed provider")
    if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", config["slug"]):
        raise ValueError("slug must use lowercase letters, digits, and single hyphens, starting with a letter")
    if not isinstance(config["display_name"], str) or not config["display_name"].strip():
        raise ValueError("display_name is required")
    for key in ("display_name", "domain", "github_repository"):
        if any(character in config[key] for character in '\n\r"`$\\'):
            raise ValueError(f"Unsupported characters in {key}")
    if config["domain"] and not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,}", config["domain"]):
        raise ValueError("domain must be a hostname without a scheme or path")
    if config["github_repository"] and not re.fullmatch(
        r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", config["github_repository"]
    ):
        raise ValueError("github_repository must be owner/repository")
    if set(config["surfaces"]) != {"web", "admin", "mcp", "mobile"} or not config["surfaces"]["web"]:
        raise ValueError("surfaces must define web, admin, mcp, and mobile; web is required")
    if set(config["monitoring"]) != {"sentry", "logfire"}:
        raise ValueError("monitoring must define sentry and logfire")
    if any(type(value) is not bool for group in ("surfaces", "monitoring") for value in config[group].values()):
        raise ValueError("Surface and monitoring choices must be booleans")
    fields = provider(root)["fields"]
    if set(config["cloud_values"]) != {field["key"] for field in fields}:
        raise ValueError("cloud_values must match the provider's declared fields")
    for field in fields:
        value = config["cloud_values"][field["key"]]
        if not isinstance(value, str) or (value and not re.fullmatch(field["pattern"], value)):
            raise ValueError(f"Invalid cloud_values.{field['key']}: {field['description']}")
    if set(config["clerk"]) != {"feature", "production"}:
        raise ValueError("clerk must define feature and production")
    for environment, values in config["clerk"].items():
        if set(values) != {"publishable_key", "jwks_url"}:
            raise ValueError("Only public Clerk configuration belongs in project.json")
        key, url = values["publishable_key"], values["jwks_url"]
        if key and not re.fullmatch(r"pk_(test|live)_[A-Za-z0-9_=-]+", key):
            raise ValueError(f"Invalid clerk.{environment}.publishable_key")
        if url and not re.fullmatch(r"https://[a-zA-Z0-9.-]+/\.well-known/jwks\.json", url):
            raise ValueError(f"Invalid clerk.{environment}.jwks_url")
    return config


def new_project(root: Path, cloud: str, destination: Path) -> None:
    destination = destination.absolute()
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise ValueError("Destination must be absent or empty")
    if root.resolve() == destination.resolve() or root.resolve() in destination.resolve().parents:
        raise ValueError("Create the product outside the template checkout")
    revision = ""
    for reference in (f"refs/heads/cloud/{cloud}", f"refs/remotes/origin/cloud/{cloud}"):
        try:
            revision = run(root, "git", "rev-parse", "--verify", reference)
            break
        except ValueError:
            continue
    if not revision:
        raise ValueError(f"Fetch cloud/{cloud} before creating a project")
    source = run(root, "git", "config", "--get", "remote.origin.url")
    address = urllib.parse.urlsplit(source)
    if address.scheme in ("http", "https"):
        host = address.hostname or ""
        if address.port:
            host += f":{address.port}"
        source = urllib.parse.urlunsplit((address.scheme, host, address.path, "", ""))
    archive = subprocess.run(["git", "archive", revision], cwd=root, capture_output=True, check=True).stdout
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="project-", dir=destination.parent) as temporary:
        staging = Path(temporary) / "project"
        staging.mkdir()
        with tarfile.open(fileobj=io.BytesIO(archive)) as tree:
            for member in tree.getmembers():
                if any(
                    part in (".env", ".adc.json", ".netrc", ".venv", "node_modules", ".terraform")
                    for part in Path(member.name).parts
                ):
                    continue
                if re.search(r"\.tfstate(?:\.|$)", member.name):
                    continue
                target = staging / member.name
                if not target.resolve().is_relative_to(staging.resolve()) or member.issym() or member.islnk():
                    raise ValueError(f"Unsupported archive entry: {member.name}")
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                elif member.isfile():
                    stream = tree.extractfile(member)
                    if stream is None:
                        raise ValueError(f"Cannot extract {member.name}")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(stream.read())
                    target.chmod(member.mode)
        metadata = provider(staging)
        if metadata["cloud"] != cloud:
            raise ValueError("Cloud snapshot contains the wrong provider")
        installed = list((staging / "library/providers").glob("*/pyproject.toml"))
        if len(installed) != 1 or installed[0].parent.name != cloud:
            raise ValueError("Cloud snapshot must contain exactly one provider")
        files: dict[str, str] = {}
        for path in staging.rglob("*"):
            relative = path.relative_to(staging).as_posix()
            if not path.is_file() or not any(fnmatch.fnmatch(relative, scope) for scope in SCOPES):
                continue
            if any(fnmatch.fnmatch(relative, pattern) for pattern in EXCLUDED):
                continue
            try:
                files[relative] = path.read_text()
            except UnicodeDecodeError:
                continue
        config = {
            "version": 1,
            "source": {"repository": source, "revision": revision},
            "cloud": cloud,
            "slug": destination.name,
            "display_name": destination.name,
            "domain": "",
            "github_repository": "",
            "cloud_values": {field["key"]: "" for field in metadata["fields"]},
            "clerk": {
                environment: {"publishable_key": "", "jwks_url": ""} for environment in ("feature", "production")
            },
            "surfaces": {"web": True, "admin": False, "mcp": False, "mobile": False},
            "monitoring": {"sentry": False, "logfire": False},
        }
        save(staging / CONFIG, config)
        configuration(staging)
        save(staging / STATE, {"files": files, "rendered": {}, "regenerate_pending": False})
        run(staging, "git", "init", "--initial-branch=main")
        if destination.exists():
            destination.rmdir()
        staging.rename(destination)
    print(
        f"Created {destination} from cloud/{cloud} at {revision}. Git history starts on main; no remote is configured."
    )
    print("Edit project.json, then run ./infrastructure/cli/_bin/m configure-project to preview the changes.")


def render(root: Path, config: dict[str, Any], files: dict[str, str]) -> dict[str, bytes]:
    outputs: dict[str, bytes] = {}
    for relative, original in files.items():
        content = original
        for field in provider(root)["fields"]:
            value = config["cloud_values"][field["key"]]
            for mapping in field.get("mappings", [field]):
                if not value or not any(fnmatch.fnmatch(relative, pattern) for pattern in mapping["paths"]):
                    continue
                if mapping.get("selector"):
                    content = "".join(
                        line.replace(mapping["placeholder"], value) if re.search(mapping["selector"], line) else line
                        for line in content.splitlines(keepends=True)
                    )
                else:
                    content = content.replace(mapping["placeholder"], value)
        if config["github_repository"]:
            content = content.replace("mention-ai-inc/app-template", config["github_repository"])
        if config["domain"]:
            content = content.replace("acme.example.com", config["domain"])
        for environment, values in config["clerk"].items():
            if relative == f"infrastructure/terraform/modules/environment/{environment}.tf":
                placeholder = "pk_test_REPLACE_ME" if environment == "feature" else "pk_live_REPLACE_ME"
                if values["publishable_key"]:
                    content = content.replace(placeholder, values["publishable_key"])
                if values["jwks_url"]:
                    content = content.replace(
                        f"https://{environment}.clerk.example.com/.well-known/jwks.json", values["jwks_url"]
                    )
        content = re.sub(r"\bacme\b", config["slug"], content)
        content = re.sub(r"\bAcme\b", config["display_name"], content)
        if relative == "README.md":
            content = (
                f"# {config['display_name']}\n\n"
                f"A product using the {config['cloud'].upper()} provider.\n\n"
                "Follow [Getting started](docs/getting-started.md) to complete setup. "
                "Project configuration is in `project.json`; product requirements and design live in `docs/product/`.\n\n"
                "This repository uses ordinary main-branch development. "
                "The original template revision is recorded in `project.json`; future updates are adopted selectively.\n"
            )
        if relative == "apps/web/index.html":
            content = re.sub(r"<title>.*?</title>", f"<title>{html.escape(config['display_name'])}</title>", content)
        if relative == "apps/mobile/app.json":
            app = json.loads(content)
            app["expo"]["name"] = config["display_name"]
            identifier = ".".join(reversed((config["domain"] or f"{config['slug']}.example.com").split(".")))
            identifier = identifier.replace("-", "")
            if "ios" in app["expo"]:
                app["expo"]["ios"]["bundleIdentifier"] = identifier
            if "android" in app["expo"]:
                app["expo"]["android"]["package"] = identifier
            content = json.dumps(app, indent=2) + "\n"
        target = relative.replace("packages/acme-api", f"packages/{config['slug']}-api")
        if content != original or target != relative:
            outputs[target] = content.encode()
    settings = {
        "enable_sentry": config["monitoring"]["sentry"],
        "enable_logfire": config["monitoring"]["logfire"],
    }
    for component in ("services", "admin"):
        outputs[f"infrastructure/terraform/configurations/{component}/project.auto.tfvars.json"] = (
            json.dumps(settings, indent=2) + "\n"
        ).encode()
    return outputs


def recover(root: Path) -> None:
    journal = root / JOURNAL
    if not journal.exists():
        return
    for relative, value in load(journal)["backups"].items():
        path = root / relative
        if value is None:
            path.unlink(missing_ok=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(base64.b64decode(value))
    journal.unlink()
    print("Recovered the interrupted configuration transaction.")


def regenerate(root: Path) -> None:
    for target in ("init", "compile-api", "sync-agent-parity"):
        result = subprocess.run([str(root / "infrastructure/cli/_bin/m"), target], cwd=root)
        if result.returncode:
            raise ValueError(f"m {target} failed. Fix the reported issue and rerun configure-project -- --apply.")


def configure(root: Path, apply: bool) -> None:
    if (root / JOURNAL).exists():
        if not apply:
            raise ValueError("Configuration was interrupted. Rerun with --apply to recover first.")
        recover(root)
    config, state = configuration(root), load(root / STATE)
    files: dict[str, str] = state["files"]
    outputs = render(root, config, files)
    previous: dict[str, str] = state["rendered"]
    changes: dict[str, bytes | None] = {}
    for relative in sorted(set(outputs) | set(previous)):
        path = root / relative
        expected = outputs.get(relative)
        current = path.read_bytes() if path.exists() else None
        baseline = previous.get(relative)
        if baseline is None and relative in files:
            baseline = digest(files[relative].encode())
        if expected is not None and previous.get(relative) == digest(expected):
            continue
        if current == expected:
            continue
        if path.is_symlink() or (current is not None and (baseline is None or digest(current) != baseline)):
            raise ValueError(
                f"Manual edits conflict with configuration: {relative}. Preserve or reconcile them before applying."
            )
        changes[relative] = expected
    for relative in files:
        if relative.startswith("packages/acme-api") and config["slug"] != "acme" and (root / relative).exists():
            if (root / relative).read_bytes() != files[relative].encode():
                raise ValueError(f"Manual edits conflict with package rename: {relative}")
            changes[relative] = None
    for relative, content in changes.items():
        print(f"{'remove' if content is None else 'write'} {relative}")
    if not apply:
        print(
            f"{len(changes)} file changes. Use --apply to configure and regenerate dependencies, clients, and agent mirrors."
        )
        return
    if changes:
        backups = {
            relative: base64.b64encode((root / relative).read_bytes()).decode() if (root / relative).exists() else None
            for relative in changes
        }
        backups[STATE] = base64.b64encode((root / STATE).read_bytes()).decode()
        save(root / JOURNAL, {"backups": backups})
        try:
            for relative, content in changes.items():
                path = root / relative
                if content is None:
                    path.unlink(missing_ok=True)
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(content)
            state.update(
                rendered={relative: digest(content) for relative, content in outputs.items()}, regenerate_pending=True
            )
            save(root / STATE, state)
            (root / JOURNAL).unlink()
        except OSError:
            recover(root)
            raise
    if state["regenerate_pending"]:
        regenerate(root)
        state["regenerate_pending"] = False
        save(root / STATE, state)
    print("Project configuration is current. Run m doctor -- --stage local.")


def settings(root: Path, github: bool = False) -> None:
    config = (
        configuration(root)
        if (root / CONFIG).exists()
        else {
            "surfaces": dict.fromkeys(("web", "admin", "mcp", "mobile"), True),
            "monitoring": dict.fromkeys(("sentry", "logfire"), True),
        }
    )
    for group in ("surfaces", "monitoring"):
        for key, value in config[group].items():
            print(f"{key if github else 'PROJECT_ENABLE_' + key.upper()}={str(value).lower()}")


def doctor(root: Path, stage: str, as_json: bool) -> int:
    checks: list[dict[str, str]] = []
    for executable in ("git", "python3", "node", "uv", "pnpm"):
        available = shutil.which(executable)
        checks.append(
            {
                "check": executable,
                "status": "pass" if available else "blocked",
                "detail": available or f"Install {executable}; see docs/getting-started.md",
            }
        )
    try:
        if shutil.which("node"):
            version = run(root, "node", "--version")
            checks.append(
                {
                    "check": "node-version",
                    "status": "pass" if int(version.lstrip("v").split(".")[0]) >= 22 else "blocked",
                    "detail": "Node 22 or newer is required",
                }
            )
        if shutil.which("pnpm"):
            version = run(root, "pnpm", "--version")
            checks.append(
                {
                    "check": "pnpm-version",
                    "status": "pass" if version.startswith("10.") else "blocked",
                    "detail": "Use pnpm 10 from package.json",
                }
            )
        config = configuration(root)
        state = load(root / STATE)
        unconfigured = any(
            state["rendered"].get(path) != digest(content)
            for path, content in render(root, config, state["files"]).items()
        )
        checks.append(
            {
                "check": "configuration",
                "status": "blocked"
                if unconfigured or state["regenerate_pending"] or (root / JOURNAL).exists()
                else "pass",
                "detail": "Run m configure-project -- --apply after changing project.json",
            }
        )
        if stage in ("cloud", "demo"):
            metadata = provider(root)
            values = {
                **config["cloud_values"],
                "domain": config["domain"],
                "github_repository": config["github_repository"],
            }
            required = ["domain", "github_repository"] + [
                field["key"] for field in metadata["fields"] if field.get("foundation", True) or stage == "demo"
            ]
            for key in required:
                value = values[key]
                checks.append(
                    {
                        "check": key,
                        "status": "pass" if value else "blocked",
                        "detail": "Configured" if value else f"Set {key} following docs/bootstrap.md",
                    }
                )
            for command in metadata["checks"]:
                if command.get("stage") == "demo" and stage != "demo":
                    continue
                if command.get("integration") and not config["monitoring"][command["integration"]]:
                    continue
                if any(not values.get(field) for field in command.get("requires", [])):
                    checks.append(
                        {
                            "check": command["name"],
                            "status": "blocked",
                            "detail": "Configure the required cloud identifiers first",
                        }
                    )
                    continue
                try:
                    arguments = [argument.format_map(values) for argument in command["command"]]
                    output = run(root, *arguments, timeout=30)
                    if command.get("equals") and output != command["equals"].format_map(values):
                        raise ValueError("The active identity does not match the configured account")
                    if command.get("nonempty") and output in ("", "null", "None", "[]", "{}"):
                        raise ValueError("No active secret version was found")
                    checks.append({"check": command["name"], "status": "pass", "detail": "Read-only check succeeded"})
                except (ValueError, OSError, subprocess.TimeoutExpired):
                    checks.append({"check": command["name"], "status": "blocked", "detail": command["remedy"]})
            for key, value in config["clerk"]["feature"].items():
                checks.append(
                    {
                        "check": f"clerk.feature.{key}",
                        "status": "pass" if value else "blocked",
                        "detail": "Configured" if value else "Complete the Clerk setup in docs/getting-started.md",
                    }
                )
        if stage == "demo" and config["domain"]:
            url = f"https://demoapi.{config['domain']}/rest/notes/health"
            try:
                with urllib.request.urlopen(url, timeout=15) as response:
                    healthy = response.status == 200
            except (OSError, urllib.error.URLError):
                healthy = False
            checks.append({"check": "notes-health", "status": "pass" if healthy else "blocked", "detail": url})
            checks.append(
                {
                    "check": "authenticated-walkthrough",
                    "status": "manual",
                    "detail": "Sign in, create an organization and note, and wait for its summary. Health alone does not verify this.",
                }
            )
    except (ValueError, OSError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        checks.append({"check": "project", "status": "blocked", "detail": str(error)})
    if as_json:
        print(json.dumps({"stage": stage, "checks": checks}, indent=2))
    else:
        for check in checks:
            print(f"{check['status'].upper()} {check['check']}: {check['detail']}")
    return int(any(check["status"] == "blocked" for check in checks))


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    new = commands.add_parser("new")
    new.add_argument("--cloud", choices=("gcp", "aws", "azure"), required=True)
    new.add_argument("--directory", type=Path, required=True)
    configure_command = commands.add_parser("configure")
    configure_command.add_argument("--apply", action="store_true")
    doctor_command = commands.add_parser("doctor")
    doctor_command.add_argument("--stage", choices=("local", "cloud", "demo"), default="local")
    doctor_command.add_argument("--json", action="store_true")
    settings_command = commands.add_parser("settings")
    settings_command.add_argument("--github", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "new":
            new_project(ROOT, args.cloud, args.directory)
        elif args.command == "configure":
            configure(ROOT, args.apply)
        elif args.command == "doctor":
            return doctor(ROOT, args.stage, args.json)
        else:
            settings(ROOT, args.github)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(f"Setup error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
