import pytest


@pytest.fixture(autouse=True)
def _set_service_env(monkeypatch: pytest.MonkeyPatch) -> None:  # pyright: ignore[reportUnusedFunction]
    """Aggregates that emit commands read `SERVICE` from the environment."""
    monkeypatch.setenv("SERVICE", "notes")
