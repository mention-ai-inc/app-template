import json
import os
import pty
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest
from mention_template import __version__
from mention_template.templates import CLOUDS

pytestmark = pytest.mark.skipif(
    not os.getenv("MENTION_TEMPLATE_ARTIFACTS"), reason="Run m test-template-release after building release artifacts"
)


@pytest.fixture(scope="module")
def artifacts() -> Path:
    return Path(os.environ["MENTION_TEMPLATE_ARTIFACTS"])


@pytest.fixture(scope="module")
def installed(artifacts: Path, tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    root = tmp_path_factory.mktemp("installed-launcher")
    environment = root / "environment"
    subprocess.run(["uv", "venv", "--python", sys.executable, str(environment)], check=True, capture_output=True)
    python = environment / "bin/python"
    wheel = next(artifacts.glob("*.whl"))
    subprocess.run(["uv", "pip", "install", "--python", str(python), str(wheel)], check=True, capture_output=True)
    return root, python


def test_distributions_include_same_manifest_and_no_dependencies(artifacts: Path) -> None:
    expected = json.loads((artifacts / "templates.json").read_text())
    with zipfile.ZipFile(next(artifacts.glob("*.whl"))) as wheel:
        assert json.loads(wheel.read("mention_template/templates.json")) == expected
        metadata = wheel.read(next(name for name in wheel.namelist() if name.endswith(".dist-info/METADATA"))).decode()
        assert "Requires-Dist:" not in metadata
    with tarfile.open(next(artifacts.glob("mention_template-*.tar.gz"))) as source:
        resource = source.extractfile(next(member for member in source if member.name.endswith("/templates.json")))
        assert resource is not None
        assert json.load(resource) == expected


def test_installed_entrypoint_outside_checkout(installed: tuple[Path, Path]) -> None:
    root, python = installed
    env = {key: value for key, value in os.environ.items() if key not in ("PYTHONPATH", "VIRTUAL_ENV")}
    result = subprocess.run(
        [str(python.parent / "mention-template"), "--version"],
        cwd=root,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )
    assert result.stdout.strip() == f"mention-template {__version__}"


@pytest.mark.parametrize("cloud", CLOUDS)
@pytest.mark.parametrize("agent", ["claude", "codex"])
def test_installed_creation_and_resume(
    artifacts: Path, installed: tuple[Path, Path], tmp_path: Path, cloud: str, agent: str
) -> None:
    _, python = installed
    binary = tmp_path / "bin"
    binary.mkdir()
    executable = binary / agent
    executable.write_text(
        f"#!{python}\n"
        "import json, os, sys\n"
        "from pathlib import Path\n"
        "Path(os.environ['AGENT_TRACE']).write_text(json.dumps({'cwd': os.getcwd(), 'tty': sys.stdin.isatty(), 'args': sys.argv[1:]}))\n"
    )
    executable.chmod(0o755)
    destination = tmp_path / f"{cloud}-product"
    trace = tmp_path / "trace"
    env = {
        **{key: value for key, value in os.environ.items() if key not in ("PYTHONPATH", "VIRTUAL_ENV")},
        "PATH": f"{binary}:{os.environ['PATH']}",
        "AGENT_TRACE": str(trace),
        "SNAPSHOT_FILE": str(artifacts / f"{cloud}.tar.gz"),
    }
    driver = (
        "import os,sys\n"
        "from unittest.mock import patch\n"
        "from mention_template.cli import main\n"
        "with patch('mention_template.templates.urllib.request.urlopen', return_value=open(os.environ['SNAPSHOT_FILE'], 'rb')):\n"
        "    raise SystemExit(main())\n"
    )
    master, slave = pty.openpty()
    try:
        process = subprocess.Popen(
            [str(python), "-c", driver, "--agent", agent, "--cloud", cloud, "--directory", str(destination)],
            cwd=tmp_path,
            env=env,
            stdin=slave,
            stdout=slave,
            stderr=slave,
        )
        assert process.wait(timeout=30) == 0
        first_trace = json.loads(trace.read_text())
        assert first_trace["tty"]
        assert Path(first_trace["cwd"]).resolve() == destination.resolve()
        assert len(first_trace["args"]) == 1
        assert not (destination / ".github/workflows/template-release.yaml").exists()
        assert not (destination / "tools/mention-template/.venv").exists()
        state = (destination / "project.json").read_bytes()
        process = subprocess.Popen(
            [str(python.parent / "mention-template"), "resume", str(destination), "--agent", agent],
            cwd=tmp_path,
            env=env,
            stdin=slave,
            stdout=slave,
            stderr=slave,
        )
        assert process.wait(timeout=15) == 0
        assert (destination / "project.json").read_bytes() == state
    finally:
        os.close(master)
        os.close(slave)
    subprocess.run(
        [str(destination / "infrastructure/cli/_bin/m"), "configure-project"],
        cwd=destination,
        env=env,
        check=True,
        capture_output=True,
        timeout=30,
    )
    subprocess.run(
        [str(destination / "infrastructure/cli/_bin/m"), "check-agent-parity"],
        cwd=destination,
        env=env,
        check=True,
        capture_output=True,
        timeout=30,
    )
