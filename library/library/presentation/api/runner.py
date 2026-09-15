import asyncio
import os
from typing import Any

from fastapi import FastAPI
from fastapi.routing import APIRoute
from gunicorn.app.base import BaseApplication

from library.providers.registry import get_cloud_provider

DEFAULT_WORKERS = 1


def run(
    *,
    app: FastAPI,
    host: str = "0.0.0.0",
    port: int = 8080,
    worker_class: str = "uvicorn_worker.UvicornWorker",
    timeout: int | None = None,
) -> None:
    options = {
        "bind": f"{host}:{port}",
        "workers": os.getenv("GUNICORN_WORKERS", str(DEFAULT_WORKERS)),
        "worker_class": worker_class,
        "loglevel": "warning",
        "accesslog": None,
        "errorlog": "/dev/null",
        "timeout": timeout or int(os.getenv("GUNICORN_TIMEOUT", "0")),
    }
    __FastAPIGunicornApplication(app, options).run()


def run_pool(*, app: FastAPI, timeout: int | None = None) -> None:
    driver = get_cloud_provider().pool_driver()
    if driver is None:
        run(app=app, timeout=timeout)
        return
    asyncio.run(driver(app=app, routes=__routes_by_name(app)))


def __routes_by_name(app: FastAPI, /) -> dict[str, str]:
    return {route.name: route.path for route in app.routes if isinstance(route, APIRoute)}


class __FastAPIGunicornApplication(BaseApplication):
    def __init__(self, app: FastAPI, options: dict[str, Any]) -> None:
        self.options = options
        self.application = app
        super().__init__()

    def load_config(self) -> None:
        if self.cfg is None:
            return
        for key, value in self.options.items():
            if key in self.cfg.settings:
                self.cfg.set(key.lower(), value)

    def load(self) -> FastAPI:
        return self.application
