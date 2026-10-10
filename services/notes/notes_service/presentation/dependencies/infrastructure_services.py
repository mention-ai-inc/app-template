from notes_service.domain.interfaces.summarizer import ISummarizer
from notes_service.infrastructure.services.summarizer.service import Summarizer


def get_summarizer() -> ISummarizer:
    return Summarizer()
