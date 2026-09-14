import logging
import os
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, Depends, FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.params import Depends as DependsParam
from fastapi.routing import APIRoute
from starlette.routing import BaseRoute
from starlette.types import StatelessLifespan

from library.infrastructure.cloud.constants import (
    APP_DOMAIN,
    COMMAND_PATH_PREFIX,
    DEAD_LETTER_PATH_SUFFIX,
    EVENT_PATH_PREFIX,
    TRIGGER_PATH_PREFIX,
)
from library.infrastructure.persistence.cache.base import aclose_cache_pool
from library.logs import SIMPLE_LOGGER_NAME
from library.presentation.api.commands import publish_command_result
from library.presentation.api.environment import ComponentType
from library.presentation.api.error_handling import ExceptionHandlingRoute
from library.presentation.api.health import HEALTH_PATH, HealthResponse, health_handler

logger = logging.getLogger(SIMPLE_LOGGER_NAME)
CORS_ORIGINS = [
    "http://localhost:3000",
    (
        f"https://{os.getenv('FEATURE_ENVIRONMENT')}{APP_DOMAIN}"
        if os.getenv("FEATURE_ENVIRONMENT")
        else f"https://{APP_DOMAIN}"
    ),
]
NO_LOG_PATHS = ["docs", "openapi", "openapi.json", "health"]


@dataclass(frozen=True)
class Entrypoint:
    handler: Callable[..., Any]
    kind: ComponentType
    preloader: Callable[[], Awaitable[None]] | None = None
    on_shutdown: Callable[[], Awaitable[None]] | None = None


def create_server_app(
    *,
    description: str,
    routers: list[APIRouter],
    prefix: str | None = None,
    routers_by_prefix: dict[str, list[APIRouter]] | None = None,
    preloader: Callable[[], Awaitable[None]] | None = None,
    on_shutdown: Callable[[], Awaitable[None]] | None = None,
) -> FastAPI:
    service = os.getenv("SERVICE", "")
    resolved_prefix = f"/rest/{service}" if prefix is None else prefix
    title = f"{service.title()} API ({os.getenv('FEATURE_ENVIRONMENT', '')})"

    api = FastAPI(
        title=title,
        description=description,
        openapi_url=f"{resolved_prefix}/openapi",
        docs_url=f"{resolved_prefix}/docs",
        lifespan=__lifespan(preloader=preloader, on_shutdown=on_shutdown),
    )
    main_router = APIRouter(prefix=resolved_prefix)

    for router in routers or []:
        __wrap_router_in_exception_handling(router=router)
        main_router.include_router(router)

    __add_health_route(router=main_router)
    api.include_router(main_router)

    for extra_prefix, extra_routers in (routers_by_prefix or {}).items():
        extra_router = APIRouter(prefix=extra_prefix)
        for router in extra_routers:
            __wrap_router_in_exception_handling(router=router)
            extra_router.include_router(router)
        __add_health_route(router=extra_router)
        api.include_router(extra_router)

    api.add_middleware(
        CORSMiddleware, allow_origins=CORS_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
    )

    for route in api.routes:
        if isinstance(route, ExceptionHandlingRoute):
            route.operation_id = route.name

    return api


def listener(
    handler: Callable[..., Any],
    /,
    *,
    preloader: Callable[[], Awaitable[None]] | None = None,
    on_shutdown: Callable[[], Awaitable[None]] | None = None,
) -> Entrypoint:
    return Entrypoint(handler=handler, kind=ComponentType.LISTENER, preloader=preloader, on_shutdown=on_shutdown)


def executor(
    handler: Callable[..., Any],
    /,
    *,
    preloader: Callable[[], Awaitable[None]] | None = None,
    on_shutdown: Callable[[], Awaitable[None]] | None = None,
) -> Entrypoint:
    return Entrypoint(handler=handler, kind=ComponentType.EXECUTOR, preloader=preloader, on_shutdown=on_shutdown)


def trigger(
    handler: Callable[..., Any],
    /,
    *,
    preloader: Callable[[], Awaitable[None]] | None = None,
    on_shutdown: Callable[[], Awaitable[None]] | None = None,
) -> Entrypoint:
    return Entrypoint(handler=handler, kind=ComponentType.TRIGGER, preloader=preloader, on_shutdown=on_shutdown)


def executor_pool(entrypoints: dict[str, Entrypoint], /) -> FastAPI:
    return __pool(
        entrypoints=entrypoints,
        kind=ComponentType.EXECUTOR,
        path_prefix=COMMAND_PATH_PREFIX,
        dependencies=[Depends(publish_command_result)],
    )


def listener_pool(entrypoints: dict[str, Entrypoint], /) -> FastAPI:
    return __pool(
        entrypoints=entrypoints,
        kind=ComponentType.LISTENER,
        path_prefix=EVENT_PATH_PREFIX,
        dead_letter=True,
    )


def trigger_pool(entrypoints: dict[str, Entrypoint], /) -> FastAPI:
    return __pool(entrypoints=entrypoints, kind=ComponentType.TRIGGER, path_prefix=TRIGGER_PATH_PREFIX)


def __pool(
    *,
    entrypoints: dict[str, Entrypoint],
    kind: ComponentType,
    path_prefix: str,
    dependencies: list[DependsParam] | None = None,
    dead_letter: bool = False,
) -> FastAPI:
    if not entrypoints:
        raise ValueError(f"A {kind} pool needs at least one entrypoint")

    mismatched = {name: entrypoint.kind for name, entrypoint in entrypoints.items() if entrypoint.kind is not kind}
    if mismatched:
        raise ValueError(f"A {kind} pool cannot host {mismatched}")

    api = FastAPI(
        lifespan=__lifespan(
            preloader=__in_sequence(*(entrypoint.preloader for entrypoint in entrypoints.values())),
            on_shutdown=__in_sequence(*(entrypoint.on_shutdown for entrypoint in entrypoints.values())),
        )
    )
    router = APIRouter()

    for name, entrypoint in entrypoints.items():
        router.post(f"{path_prefix}/{name}", name=name, dependencies=dependencies or [])(entrypoint.handler)
        if dead_letter:
            router.post(f"{path_prefix}/{name}{DEAD_LETTER_PATH_SUFFIX}", name=f"{name}_dead_letter")(
                __acknowledge_dead_letter
            )

    router.routes = [
        __wrap_route_in_exception_handling(route=route) for route in router.routes if isinstance(route, APIRoute)
    ]

    __add_health_route(router=router)
    api.include_router(router)

    return api


async def __acknowledge_dead_letter() -> Response:
    return Response(status_code=200)


def __in_sequence(*callbacks: Callable[[], Awaitable[None]] | None) -> Callable[[], Awaitable[None]] | None:
    present = [callback for callback in callbacks if callback is not None]
    if not present:
        return None

    async def run_in_sequence() -> None:
        for callback in present:
            await callback()

    return run_in_sequence


def __wrap_router_in_exception_handling(*, router: APIRouter) -> None:
    new_routes: list[BaseRoute] = []
    for route in router.routes:
        if isinstance(route, APIRoute):
            new_routes.append(__wrap_route_in_exception_handling(route=route))

    router.routes = new_routes


def __wrap_route_in_exception_handling(*, route: APIRoute) -> BaseRoute:
    new_route = ExceptionHandlingRoute(
        path=route.path,
        endpoint=route.endpoint,
        methods=route.methods,
        name=route.name,
        dependencies=route.dependencies,
        response_class=route.response_class,
        responses=route.responses,
        response_model=route.response_model,
        tags=route.tags,
    )
    return new_route


def __add_health_route(*, router: APIRouter | FastAPI) -> None:
    health_router = APIRouter(tags=["Health"])
    health_router.get(HEALTH_PATH, response_model=HealthResponse, operation_id="health")(health_handler)
    router.include_router(health_router)


def __lifespan(
    *, preloader: Callable[[], Awaitable[None]] | None, on_shutdown: Callable[[], Awaitable[None]] | None
) -> StatelessLifespan[FastAPI]:
    @asynccontextmanager
    async def lifespan_fn(app: FastAPI) -> AsyncGenerator[None]:  # noqa: ARG001
        if preloader:
            await preloader()
        yield
        if on_shutdown:
            await on_shutdown()
        await aclose_cache_pool()

    return lifespan_fn
