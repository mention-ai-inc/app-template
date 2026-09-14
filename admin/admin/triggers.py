from library.presentation.api.app import trigger_pool
from library.presentation.api.runner import run
from library.presentation.service.triggers.publish_audit_event import publish_audit_event

ENTRYPOINTS = {"publish_audit_event": publish_audit_event}

app = trigger_pool(ENTRYPOINTS)


def main() -> None:
    run(app=app)
