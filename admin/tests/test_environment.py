from __future__ import annotations

import pytest

from admin.common.environment import (
    SEED_ORGANIZATION_VARIABLE,
    default_seed_organization_id,
    feature_environment,
    require_feature_environment,
)


def test_require_feature_environment_returns_value_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FEATURE_ENVIRONMENT", "issue294")
    assert require_feature_environment() == "issue294"


def test_require_feature_environment_raises_when_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FEATURE_ENVIRONMENT", "")
    with pytest.raises(SystemExit):
        require_feature_environment()


def test_feature_environment_defaults_to_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FEATURE_ENVIRONMENT", raising=False)
    assert feature_environment() == ""


def test_default_seed_organization_id_reads_environment_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(SEED_ORGANIZATION_VARIABLE, "org_from_env")
    assert default_seed_organization_id() == "org_from_env"


def test_default_seed_organization_id_is_none_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(SEED_ORGANIZATION_VARIABLE, raising=False)
    assert default_seed_organization_id() is None
