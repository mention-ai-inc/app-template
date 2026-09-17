import pytest
from mention_template.deployment import plan


@pytest.mark.parametrize("auto", [True, False])
@pytest.mark.parametrize("target", ["demo", "production"])
def test_manual_overrides_pause(auto: bool, target: str) -> None:
    config = {"deployment": {"auto_demo": auto}, "surfaces": {"web": True, "mcp": False, "admin": False}}
    result = plan(
        config, "workflow_dispatch", {"inputs": {"environment": target, "notes": "true", "web": "true", "mcp": "true"}}
    )
    assert result["enabled"] == "true"
    assert result["target"] == target
    assert result["mcp"] == "false"
    assert result["full_demo"] == str(target == "demo").lower()


@pytest.mark.parametrize("auto", [True, False, None])
def test_merge_respects_pause(auto: bool | None) -> None:
    config = {"surfaces": {"web": True, "mcp": True, "admin": True}}
    if auto is not None:
        config["deployment"] = {"auto_demo": auto}
    result = plan(config, "pull_request", {"pull_request": {"merged": True}})
    assert result["enabled"] == str(auto is not False).lower()
    assert result["full_demo"] == result["enabled"]
    assert result["terraform_operations"] == "false"


def test_manual_defaults_to_production_and_partial_demo_keeps_baseline() -> None:
    config = {"surfaces": {"web": True, "mcp": False, "admin": False}}
    assert plan(config, "workflow_dispatch", {"inputs": {}})["target"] == "production"
    result = plan(config, "workflow_dispatch", {"inputs": {"environment": "demo", "notes": True}})
    assert result["full_demo"] == "false"
    assert result["notes"] == "true"
    assert result["web"] == "false"


def test_unmerged_pr_does_not_deploy() -> None:
    config = {"surfaces": {"web": True, "mcp": True, "admin": True}}
    result = plan(config, "pull_request", {"pull_request": {"merged": False}})
    assert result["enabled"] == "false"


def test_invalid_environment_is_rejected() -> None:
    with pytest.raises(ValueError, match="Select"):
        plan({"surfaces": {}}, "workflow_dispatch", {"inputs": {"environment": "unexpected"}})
