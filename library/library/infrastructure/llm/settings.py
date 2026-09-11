from pydantic_ai.settings import ModelSettings, ThinkingLevel


def model_settings(
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
    thinking: ThinkingLevel | None = None,
) -> ModelSettings:
    settings = ModelSettings()

    if temperature is not None:
        settings["temperature"] = temperature
    if max_tokens is not None:
        settings["max_tokens"] = max_tokens
    if thinking is not None:
        settings["thinking"] = thinking

    return settings
