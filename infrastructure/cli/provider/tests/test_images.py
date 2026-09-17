from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]


@pytest.mark.parametrize("failure", ["true", "false"])
def test_image_publication_cleans_credentials_on_success_and_failure(tmp_path: Path, failure: str) -> None:
    cli = tmp_path / "infrastructure/cli"
    cli.mkdir(parents=True)
    (tmp_path / ".agents").mkdir()
    (cli / "Makefile").write_text(
        ".ONESHELL:\nSHELL:=/bin/bash\n" + (ROOT / "infrastructure/cli/provider/onboarding.mk").read_text()
    )
    module = tmp_path / "infrastructure/terraform/modules/compute-engine-redis"
    module.mkdir(parents=True)
    (module / "cache-images.json").write_bytes(
        (ROOT / "infrastructure/terraform/modules/compute-engine-redis/cache-images.json").read_bytes()
    )
    (tmp_path / "project.json").write_text(
        json.dumps(
            {
                "cloud_values": {
                    "operations_project_id": "example-operations",
                    "region": "us-central1",
                    "engineer_email": "engineer@example.org",
                }
            }
        )
    )
    binary = tmp_path / "bin"
    binary.mkdir()
    docker = binary / "docker"
    docker.write_text("""#!/bin/bash
printf '%s\n' "$*" >> "$FAKE_TRACE"
if [ "$1" = context ]; then
    echo unix:///test/docker.sock
    exit 0
fi
printf '%s' "$DOCKER_CONFIG" > "$FAKE_CONFIG"
if [ "$3" = pull ] && [ "$FAIL_PULL" = true ]; then exit 1; fi
""")
    docker.chmod(0o755)
    cloud = binary / "gcloud"
    cloud.write_text(
        '#!/bin/bash\nprintf \'%s\' \'{"credHelpers":{"example":"gcloud"}}\' > "$DOCKER_CONFIG/config.json"\n'
    )
    cloud.chmod(0o755)
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    environment = {
        **os.environ,
        "PATH": f"{binary}:{os.environ['PATH']}",
        "FAIL_PULL": failure,
        "FAKE_TRACE": str(tmp_path / "trace"),
        "FAKE_CONFIG": str(tmp_path / "docker-config"),
    }
    result = subprocess.run(
        [str(ROOT / "infrastructure/cli/_bin/m"), "publish-cache-images"],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
    )
    assert (result.returncode != 0) == (failure == "true")
    assert not Path((tmp_path / "docker-config").read_text()).exists()
    trace = (tmp_path / "trace").read_text()
    if failure == "true":
        assert " push " not in trace and " tag " not in trace
    else:
        assert trace.count(" push ") == 2
    assert not (tmp_path / "config.json").exists()
