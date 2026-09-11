from library.domain.value_objects.core import EnumValueObject


class LLMModelName(EnumValueObject):
    GEMINI_36_FLASH = "google:gemini-3.6-flash"
    GEMINI_35_FLASH_LITE = "google:gemini-3.5-flash-lite"
