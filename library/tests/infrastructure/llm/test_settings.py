from library.infrastructure.llm.settings import model_settings


async def test_model_settings_passes_values_through() -> None:
    settings = model_settings(temperature=0.0, max_tokens=2048, thinking="medium")

    assert settings.get("temperature") == 0.0
    assert settings.get("max_tokens") == 2048
    assert settings.get("thinking") == "medium"


async def test_model_settings_omits_absent_values() -> None:
    assert model_settings() == {}
