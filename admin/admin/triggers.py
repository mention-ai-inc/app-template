from control_plane.presentation.api.app import trigger_pool
from control_plane.presentation.api.runner import run_pool
from control_plane.presentation.service.triggers.publish_audit_event import publish_audit_event

ENTRYPOINTS = {"publish_audit_event": publish_audit_event}

app = trigger_pool(ENTRYPOINTS)


def main() -> None:
    run_pool(app=app)
