from fastapi import FastAPI

from admin.common.environment import feature_environment
from admin.server.routers.backfills import router as backfills_router
from admin.server.routers.operations import router as operations_router
from admin.server.routers.organizations import router as organizations_router
from admin.server.routers.runs import router as runs_router
from admin.server.routers.seed import router as seed_router
from library.presentation.api.app import create_server_app


def create_admin_app() -> FastAPI:
    routers = [operations_router, organizations_router, backfills_router, runs_router]
    if feature_environment():
        routers.append(seed_router)
    return create_server_app(
        description="Control plane for admin operations.",
        routers=routers,
        prefix="",
    )
