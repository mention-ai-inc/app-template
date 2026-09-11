from admin.server.app import create_admin_app
from library.presentation.api.runner import run

app = create_admin_app()


def main() -> None:
    run(app=app)
