import io
import json
import os
import pty
import select
import shutil
import signal
import subprocess
import sys
import tarfile
import time
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from mention_template import __version__, agents, cli, setup, templates


@pytest.fixture
def archive() -> bytes:
    files = {
        "infrastructure/cli/provider/project.json": json.dumps({"cloud": "aws", "fields": []}),
        "library/providers/aws/pyproject.toml": '[project]\nname = "provider"\n',
        "README.md": "Acme",
        "infrastructure/cli/_bin/m": "#!/bin/bash\n",
        ".agents/skills/start-project/SKILL.md": "Guide setup",
        ".claude/skills/start-project/SKILL.md": "Guide setup",
        ".github/workflows/template-release.yaml": "must not be exported",
        ".env": "PRIVATE=secret",
        ".git/config": "credentials",
        "infrastructure/terraform/current.tfstate": "secret state",
    }
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tree:
        for name, text in files.items():
            content = text.encode()
            member = tarfile.TarInfo(name)
            member.size = len(content)
            member.mode = 0o755 if name.endswith("/m") else 0o644
            tree.addfile(member, io.BytesIO(content))
    return buffer.getvalue()


@pytest.fixture
def product(tmp_path: Path, archive: bytes) -> Path:
    destination = tmp_path / "sample-product"
    setup.initialize_project(archive, templates.REPOSITORY, "a" * 40, "aws", destination)
    return destination


def test_creation_keeps_secrets_and_release_workflow_out(product: Path) -> None:
    assert not (product / ".env").exists()
    assert not (product / ".github/workflows/template-release.yaml").exists()
    assert not (product / "infrastructure/terraform/current.tfstate").exists()
    assert "credentials" not in (product / ".git/config").read_text()
    assert os.access(product / "infrastructure/cli/_bin/m", os.X_OK)
    assert setup.run(product, "git", "branch", "--show-current") == "main"
    assert setup.run(product, "git", "remote") == ""
    agents.validate_project(product)


@pytest.mark.parametrize("entry", ["../escape", "/absolute", "link", "device"])
def test_unsafe_archive_does_not_create_destination(tmp_path: Path, entry: str) -> None:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as tree:
        member = tarfile.TarInfo(entry)
        if entry == "link":
            member.type = tarfile.SYMTYPE
            member.linkname = "../escape"
        if entry == "device":
            member.type = tarfile.CHRTYPE
        tree.addfile(member)
    destination = tmp_path / "product"
    with pytest.raises(ValueError, match="Unsupported archive"):
        setup.initialize_project(buffer.getvalue(), "", "", "aws", destination)
    assert not destination.exists()
    assert not (tmp_path / "escape").exists()


def test_cloud_mismatch_is_atomic(tmp_path: Path, archive: bytes) -> None:
    destination = tmp_path / "product"
    with pytest.raises(ValueError, match="wrong provider"):
        setup.initialize_project(archive, "", "", "azure", destination)
    assert not destination.exists()


def test_checksum_failure(tmp_path: Path) -> None:
    with patch.object(templates.urllib.request, "urlopen", return_value=io.BytesIO(b"wrong")):
        with pytest.raises(ValueError, match="checksum"):
            templates.download({"url": "https://example.org/archive", "sha256": "0" * 64})
    assert list(tmp_path.iterdir()) == []


def test_occupied_destination_is_checked_before_download(tmp_path: Path) -> None:
    (tmp_path / "keep").write_text("product work")
    with patch.object(templates, "download") as download:
        with pytest.raises(ValueError, match="absent or empty"):
            templates.create("aws", tmp_path)
    download.assert_not_called()
    assert (tmp_path / "keep").read_text() == "product work"


@pytest.mark.parametrize("failure", ["version", "url", "checksum", "revision", "missing"])
def test_invalid_manifest_is_rejected(tmp_path: Path, failure: str) -> None:
    value: dict[str, Any] = {
        "version": __version__,
        "repository": templates.REPOSITORY,
        "clouds": {
            cloud: {
                "url": f"{templates.REPOSITORY}/releases/download/template-v{__version__}/{cloud}.tar.gz",
                "sha256": "a" * 64,
                "revision": "b" * 40,
            }
            for cloud in templates.CLOUDS
        },
    }
    if failure == "version":
        value["version"] = "other"
    elif failure == "url":
        value["clouds"]["aws"]["url"] = "https://unrelated.example/archive"
    elif failure == "checksum":
        value["clouds"]["aws"]["sha256"] = ""
    elif failure == "revision":
        value["clouds"]["aws"]["revision"] = "main"
    if failure != "missing":
        (tmp_path / "templates.json").write_text(json.dumps(value))
    with patch.object(templates, "files", return_value=tmp_path):
        with pytest.raises(ValueError):
            templates.manifest()


def test_network_failure_preserves_destination(tmp_path: Path) -> None:
    destination = tmp_path / "product"
    value = {"clouds": {"aws": {"revision": "a" * 40}}}
    with (
        patch.object(templates, "manifest", return_value=value),
        patch.object(templates, "download", side_effect=OSError("offline")),
    ):
        with pytest.raises(OSError, match="offline"):
            templates.create("aws", destination)
    assert not destination.exists()


@pytest.mark.parametrize("agent", ["claude", "codex"])
def test_resume_handoff_preserves_configuration(product: Path, agent: str) -> None:
    before = (product / "project.json").read_bytes()
    with (
        patch.object(sys, "argv", ["mention-template", "resume", str(product), "--agent", agent]),
        patch.object(sys.stdin, "isatty", return_value=True),
        patch.object(sys.stdout, "isatty", return_value=True),
        patch.object(agents, "executable", return_value=f"/bin/{agent}"),
        patch.object(agents, "launch") as launch,
        patch.object(templates, "download") as download,
    ):
        assert cli.main() == 0
    launch.assert_called_once_with(agent, f"/bin/{agent}", product)
    download.assert_not_called()
    assert (product / "project.json").read_bytes() == before
    assert not setup.load(product / setup.STATE)["rendered"]


def test_missing_agent_precedes_creation(tmp_path: Path) -> None:
    with (
        patch.object(
            sys, "argv", ["mention-template", "--agent", "claude", "--cloud", "aws", "--directory", str(tmp_path)]
        ),
        patch.object(sys.stdin, "isatty", return_value=True),
        patch.object(sys.stdout, "isatty", return_value=True),
        patch.object(agents, "executable", side_effect=ValueError("Install Claude Code")),
        patch.object(templates, "create") as create,
    ):
        assert cli.main() == 1
    create.assert_not_called()


def test_noninteractive_use_is_rejected() -> None:
    with (
        patch.object(sys, "argv", ["mention-template", "--agent", "codex"]),
        patch.object(sys.stdin, "isatty", return_value=False),
        patch.object(templates, "create") as create,
    ):
        assert cli.main() == 1
    create.assert_not_called()


@pytest.mark.parametrize("agent", ["claude", "codex"])
@pytest.mark.parametrize("exit_code", [0, 7])
def test_real_terminal_handoff(product: Path, tmp_path: Path, agent: str, exit_code: int) -> None:
    binary = tmp_path / "bin"
    binary.mkdir()
    executable = binary / agent
    executable.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "from pathlib import Path\n"
        "Path(os.environ['AGENT_TRACE']).write_text(json.dumps({"
        "'cwd': os.getcwd(), 'arguments': sys.argv[1:], 'stdin': sys.stdin.isatty(), 'stdout': sys.stdout.isatty()}))\n"
        f"sys.exit({exit_code})\n"
    )
    executable.chmod(0o755)
    trace = tmp_path / "trace.json"
    env = {**os.environ, "PATH": f"{binary}:{os.environ['PATH']}", "AGENT_TRACE": str(trace)}
    master, slave = pty.openpty()
    try:
        process = subprocess.Popen(
            [sys.executable, "-m", "mention_template", "resume", str(product), "--agent", agent],
            cwd=tmp_path,
            env=env,
            stdin=slave,
            stdout=slave,
            stderr=slave,
        )
        assert process.wait(timeout=15) == exit_code
    finally:
        os.close(master)
        os.close(slave)
    record = json.loads(trace.read_text())
    assert Path(record["cwd"]).resolve() == product.resolve()
    assert record["stdin"] and record["stdout"]
    assert len(record["arguments"]) == 1
    assert "start-project/SKILL.md" in record["arguments"][0]
    assert "existing generated project" in record["arguments"][0]


def test_interrupt_preserves_project(product: Path, tmp_path: Path) -> None:
    binary = tmp_path / "bin"
    binary.mkdir()
    executable = binary / "claude"
    executable.write_text(f"#!{sys.executable}\nimport time\nprint('AGENT_READY', flush=True)\ntime.sleep(60)\n")
    executable.chmod(0o755)
    env = {**os.environ, "PATH": f"{binary}:{os.environ['PATH']}"}
    master, slave = pty.openpty()
    process = subprocess.Popen(
        [sys.executable, "-m", "mention_template", "resume", str(product), "--agent", "claude"],
        env=env,
        stdin=slave,
        stdout=slave,
        stderr=slave,
    )
    output = b""
    deadline = time.monotonic() + 15
    try:
        while b"AGENT_READY" not in output and time.monotonic() < deadline:
            if select.select([master], [], [], 0.5)[0]:
                output += os.read(master, 8192)
        assert b"AGENT_READY" in output
        process.send_signal(signal.SIGINT)
        assert process.wait(timeout=5) != 0
        agents.validate_project(product)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        os.close(master)
        os.close(slave)


def test_new_launcher_uses_snapshot_and_hands_off(tmp_path: Path, archive: bytes) -> None:
    destination = tmp_path / "new-product"
    value: dict[str, Any] = {
        "repository": templates.REPOSITORY,
        "clouds": {"aws": {"revision": "a" * 40}},
    }
    with (
        patch.object(
            sys, "argv", ["mention-template", "--agent", "codex", "--cloud", "aws", "--directory", str(destination)]
        ),
        patch.object(sys.stdin, "isatty", return_value=True),
        patch.object(sys.stdout, "isatty", return_value=True),
        patch.object(templates, "manifest", return_value=value),
        patch.object(templates, "download", return_value=archive),
        patch.object(agents, "executable", return_value="/bin/codex"),
        patch.object(agents, "launch") as launch,
    ):
        assert cli.main() == 0
    launch.assert_called_once_with("codex", "/bin/codex", destination)
    agents.validate_project(destination)


def test_invalid_resume_does_not_launch(product: Path) -> None:
    shutil.rmtree(product / ".git")
    with pytest.raises(ValueError):
        agents.validate_project(product)
