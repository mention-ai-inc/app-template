from library.presentation.api.app import executor_pool
from library.presentation.api.runner import run_pool
from notes_service.presentation.executors import summarize_note

ENTRYPOINTS = {"summarize_note": summarize_note.endpoint}

app = executor_pool(ENTRYPOINTS)


def main() -> None:
    run_pool(app=app)
