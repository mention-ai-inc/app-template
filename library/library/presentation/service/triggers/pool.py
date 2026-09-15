from library.presentation.api.app import trigger_pool
from library.presentation.api.runner import run_pool
from library.presentation.service.triggers.publish_audit_event import publish_audit_event
from library.presentation.service.triggers.publish_event import publish_event
from library.presentation.service.triggers.submit_command import submit_command

ENTRYPOINTS = {
    "publish_event": publish_event,
    "submit_command": submit_command,
    "publish_audit_event": publish_audit_event,
}

app = trigger_pool(ENTRYPOINTS)


def main() -> None:
    run_pool(app=app)
