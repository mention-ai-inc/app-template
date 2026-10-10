from control_plane.presentation.api.app import create_server_app
from control_plane.presentation.api.runner import run
from notes_service.presentation.servers.rest.routers.notes.routes import notes_router

with open("README.md") as f:
    readme = f.read().strip()

app = create_server_app(description=readme, routers=[notes_router])


def main() -> None:
    run(app=app)
