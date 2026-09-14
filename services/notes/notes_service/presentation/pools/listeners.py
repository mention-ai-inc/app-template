from library.presentation.api.app import listener_pool
from library.presentation.api.runner import run
from library.presentation.service.listeners.acknowledge import acknowledge_command_result
from notes_service.presentation.listeners import summarize_note

ENTRYPOINTS = {
    "acknowledge_command_result": acknowledge_command_result,
    "summarize_note": summarize_note.handler,
}

app = listener_pool(ENTRYPOINTS)


def main() -> None:
    run(app=app)
