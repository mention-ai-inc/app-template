import pytest

from library.application.ports.runtime import IRuntimeContext

RESOURCE_NAME = "notes-commands"


def test_the_deployment_id_is_a_non_empty_string(runtime_context: IRuntimeContext) -> None:
    deployment_id = runtime_context.get_deployment_id()

    assert isinstance(deployment_id, str)
    assert deployment_id != ""


def test_the_region_is_a_non_empty_string(runtime_context: IRuntimeContext) -> None:
    region = runtime_context.get_region()

    assert isinstance(region, str)
    assert region != ""


def test_a_scoped_resource_name_keeps_the_resource_name(runtime_context: IRuntimeContext) -> None:
    assert runtime_context.scope_resource_name(RESOURCE_NAME).endswith(RESOURCE_NAME)


def test_scoping_is_stable_across_calls(runtime_context: IRuntimeContext) -> None:
    assert runtime_context.scope_resource_name(RESOURCE_NAME) == runtime_context.scope_resource_name(RESOURCE_NAME)


def test_a_scoped_resource_name_carries_the_feature_environment(
    runtime_context: IRuntimeContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FEATURE_ENVIRONMENT", "pr7")

    assert runtime_context.scope_resource_name(RESOURCE_NAME) == f"pr7{RESOURCE_NAME}"
