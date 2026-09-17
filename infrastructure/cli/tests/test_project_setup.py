from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from mention_template import setup


@pytest.fixture(params=["gcp", "aws", "azure"])
def template(tmp_path: Path, request: pytest.FixtureRequest) -> tuple[Path, str]:
    cloud = str(request.param)
    root = tmp_path / "template"
    root.mkdir()
    files = {
        ".agents/rules.json": "{}",
        "infrastructure/cli/Makefile": "init:\n\t@true\n",
        "library/providers/" + cloud + "/pyproject.toml": '[project]\nname = "provider"\n',
        "packages/acme-api/package.json": '{"name":"@packages/acme-api"}',
        "packages/acme-api-client/package.json": '{"name":"@packages/acme-api-client"}',
        "apps/web/index.html": "<title>acme</title>",
        "apps/mobile/app.json": '{"expo":{"name":"Acme","slug":"acme"}}',
        "library/settings.py": 'DOMAIN = "acme.example.com"\n',
        "infrastructure/terraform/settings.tf": 'account = "000000000000"\n',
        "infrastructure/cli/provider/helpers/acr-login": "TOKEN_LOGIN_USERNAME=00000000-0000-0000-0000-000000000000\n",
        "infrastructure/terraform/modules/environment/feature.tf": 'clerk_publishable_key = "pk_test_REPLACE_ME"\nclerk_jwks_url = "https://feature.clerk.example.com/.well-known/jwks.json"\n',
        "README.md": "Acme uses acme at mention-ai-inc/app-template",
    }
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    metadata = {
        "cloud": cloud,
        "fields": [
            {
                "key": "account",
                "pattern": "[0-9]{12}",
                "description": "Account",
                "mappings": [{"placeholder": "000000000000", "paths": ["infrastructure/terraform/settings.tf"]}],
            }
        ],
        "checks": [],
    }
    setup.save(root / setup.PROVIDER, metadata)
    setup.run(root, "git", "init", "--initial-branch=main")
    setup.run(root, "git", "config", "user.name", "Setup test")
    setup.run(root, "git", "config", "user.email", "test@example.com")
    setup.run(root, "git", "remote", "add", "origin", "https://example.com/template.git")
    setup.run(root, "git", "add", ".")
    setup.run(root, "git", "commit", "-m", "Fixture")
    setup.run(root, "git", "branch", f"cloud/{cloud}")
    (root / ".env").write_text("SECRET=never-export-this")
    (root / "README.md").write_text("Uncommitted change")
    return root, cloud


@pytest.fixture
def product(template: tuple[Path, str], tmp_path: Path) -> Path:
    root, cloud = template
    destination = tmp_path / "new-product"
    setup.new_project(root, cloud, destination)
    config = setup.load(destination / setup.CONFIG)
    config.update(display_name="New Product", domain="product.example.org", github_repository="example/new-product")
    config["cloud_values"]["account"] = "123456789012"
    config["clerk"]["feature"] = {
        "publishable_key": "pk_test_example",
        "jwks_url": "https://feature.example.org/.well-known/jwks.json",
    }
    setup.save(destination / setup.CONFIG, config)
    return destination


def test_export_uses_committed_snapshot_without_credentials_or_history(
    product: Path, template: tuple[Path, str]
) -> None:
    root, cloud = template
    config = setup.load(product / setup.CONFIG)
    assert config["source"]["revision"] == setup.run(root, "git", "rev-parse", f"cloud/{cloud}")
    assert (product / "README.md").read_text().startswith("Acme")
    assert not (product / ".env").exists()
    assert (root / "README.md").read_text() == "Uncommitted change"
    assert setup.run(product, "git", "symbolic-ref", "--short", "HEAD") == "main"
    assert setup.run(product, "git", "remote") == ""
    assert len(list((product / "library/providers").glob("*/pyproject.toml"))) == 1


def test_nonempty_destination_is_untouched(template: tuple[Path, str], tmp_path: Path) -> None:
    root, cloud = template
    destination = tmp_path / "existing"
    destination.mkdir()
    (destination / "keep").write_text("mine")
    with pytest.raises(ValueError, match="absent or empty"):
        setup.new_project(root, cloud, destination)
    assert (destination / "keep").read_text() == "mine"


def test_preview_does_not_mutate(product: Path) -> None:
    before = {path: path.read_bytes() for path in product.rglob("*") if path.is_file()}
    setup.configure(product, False)
    assert before == {path: path.read_bytes() for path in product.rglob("*") if path.is_file()}


def test_apply_renames_and_preserves_protocol_constants(product: Path) -> None:
    with patch.object(setup, "regenerate") as regeneration:
        setup.configure(product, True)
        assert regeneration.call_count == 1
    assert (
        json.loads((product / "packages/new-product-api/package.json").read_text())["name"]
        == "@packages/new-product-api"
    )
    assert not (product / "packages/acme-api/package.json").exists()
    assert 'account = "123456789012"' in (product / "infrastructure/terraform/settings.tf").read_text()
    assert (
        "00000000-0000-0000-0000-000000000000"
        in (product / "infrastructure/cli/provider/helpers/acr-login").read_text()
    )
    assert (product / "apps/web/index.html").read_text() == "<title>New Product</title>"
    assert "feature.example.org" in (product / "infrastructure/terraform/modules/environment/feature.tf").read_text()
    assert setup.load(product / "infrastructure/terraform/configurations/services/project.auto.tfvars.json") == {
        "enable_sentry": False,
        "enable_logfire": False,
    }


def test_repeat_apply_is_noop_and_allows_unrelated_product_edits(product: Path) -> None:
    with patch.object(setup, "regenerate") as regeneration:
        setup.configure(product, True)
        path = product / "library/settings.py"
        path.write_text(path.read_text() + 'PRODUCT_SETTING = "mine"\n')
        setup.configure(product, True)
        assert regeneration.call_count == 1
        assert "PRODUCT_SETTING" in path.read_text()


def test_changed_input_reports_conflicting_manual_edit(product: Path) -> None:
    with patch.object(setup, "regenerate"):
        setup.configure(product, True)
    path = product / "library/settings.py"
    path.write_text(path.read_text() + "CUSTOM = True\n")
    config = setup.load(product / setup.CONFIG)
    config["domain"] = "changed.example.org"
    setup.save(product / setup.CONFIG, config)
    with pytest.raises(ValueError, match="Manual edits conflict"):
        setup.configure(product, True)
    assert "CUSTOM" in path.read_text()


def test_interrupted_write_rolls_back_on_next_apply(product: Path) -> None:
    original = Path.write_bytes
    failed = False

    def fail_once(path: Path, data: bytes) -> int:
        nonlocal failed
        if path.name == "index.html" and not failed:
            failed = True
            raise OSError("interrupted")
        return original(path, data)

    with patch.object(Path, "write_bytes", fail_once), pytest.raises(OSError, match="interrupted"):
        setup.configure(product, True)
    assert not (product / setup.JOURNAL).exists()
    assert (product / "apps/web/index.html").read_text() == "<title>acme</title>"
    with patch.object(setup, "regenerate"):
        setup.configure(product, True)
    assert (product / "apps/web/index.html").read_text() == "<title>New Product</title>"


def test_regeneration_failure_is_resumable(product: Path) -> None:
    with patch.object(setup, "regenerate", side_effect=ValueError("install failed")), pytest.raises(ValueError):
        setup.configure(product, True)
    assert setup.load(product / setup.STATE)["regenerate_pending"]
    with patch.object(setup, "regenerate") as regeneration:
        setup.configure(product, True)
        assert regeneration.call_count == 1
    assert not setup.load(product / setup.STATE)["regenerate_pending"]


def test_enable_optional_integrations(product: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with patch.object(setup, "regenerate"):
        setup.configure(product, True)
        config = setup.load(product / setup.CONFIG)
        config["monitoring"] = {"sentry": True, "logfire": True}
        config["surfaces"].update(admin=True, mcp=True, mobile=True)
        setup.save(product / setup.CONFIG, config)
        setup.configure(product, True)
    setup.settings(product, True)
    assert "mcp=true" in capsys.readouterr().out
    assert setup.load(product / "infrastructure/terraform/configurations/admin/project.auto.tfvars.json")[
        "enable_sentry"
    ]


def test_secret_fields_are_rejected(product: Path) -> None:
    config = setup.load(product / setup.CONFIG)
    config["clerk"]["feature"]["secret_key"] = "never-record"
    setup.save(product / setup.CONFIG, config)
    with pytest.raises(ValueError, match="Only public Clerk"):
        setup.configuration(product)


def test_local_doctor_reports_missing_tools_without_cloud_calls(
    product: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    capsys.readouterr()
    with patch.object(setup.shutil, "which", return_value=None), patch.object(setup, "run") as command:
        assert setup.doctor(product, "local", True) == 1
        command.assert_not_called()
    result = json.loads(capsys.readouterr().out)
    assert any(check["status"] == "blocked" for check in result["checks"])


def test_regeneration_stops_on_first_failed_command(product: Path) -> None:
    with patch.object(setup.subprocess, "run", return_value=subprocess.CompletedProcess([], 1)) as command:
        with pytest.raises(ValueError, match="m init failed"):
            setup.regenerate(product)
        assert command.call_count == 1


@pytest.mark.parametrize("value", [True, False, None])
def test_auto_demo_compatibility(product: Path, capsys: pytest.CaptureFixture[str], value: bool | None) -> None:
    config = setup.load(product / setup.CONFIG)
    if value is None:
        config.pop("deployment")
    else:
        config["deployment"] = {"auto_demo": value}
    setup.save(product / setup.CONFIG, config)
    setup.settings(product, True)
    assert f"auto_demo={str(value is not False).lower()}" in capsys.readouterr().out


@pytest.mark.parametrize("value", ["false", 0, None, {}, {"auto_demo": True, "unknown": True}])
def test_invalid_deployment_settings(product: Path, value: object) -> None:
    config = setup.load(product / setup.CONFIG)
    config["deployment"] = value if isinstance(value, dict) or value is None else {"auto_demo": value}
    setup.save(product / setup.CONFIG, config)
    with pytest.raises(ValueError, match="deployment"):
        setup.configuration(product)


def test_verification_checkpoint_preserved(product: Path) -> None:
    checkpoint = product / "docs/setup-verification.md"
    assert "unverified" in checkpoint.read_text()
    assert "Standalone launcher beta" not in checkpoint.read_text()
    with patch.object(setup, "regenerate"):
        setup.configure(product, True)
        checkpoint.write_text("# Setup verification\n\nSigned-in summary verified.\n")
        setup.configure(product, True)
    assert "Signed-in summary verified" in checkpoint.read_text()


def test_provider_diagnostics_rejects_unstructured_output(tmp_path: Path) -> None:
    helper = tmp_path / "infrastructure/cli/provider/helpers/doctor.py"
    helper.parent.mkdir(parents=True)
    helper.touch()
    with patch.object(setup, "run", return_value='{"token": "never-print"}'):
        result = setup.provider_diagnostics(tmp_path, "cloud")
    assert result[0]["status"] == "blocked"
    assert "never-print" not in str(result)
