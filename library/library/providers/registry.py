import os
from importlib.metadata import entry_points

from library.application.ports.provider import ICloudProvider
from library.infrastructure.errors import InfrastructureError, InfrastructureErrorType
from library.providers.local.provider import PROVIDER as LOCAL_PROVIDER

ENTRY_POINT_GROUP = "acme.cloud_provider"
BUILT_IN_PROVIDERS: dict[str, ICloudProvider] = {"local": LOCAL_PROVIDER}
DEFAULT_PROVIDER_NAME = "local"

_provider: ICloudProvider | None = None


def get_cloud_provider() -> ICloudProvider:
    global _provider
    if _provider is None:
        _provider = _resolve()
    return _provider


def set_cloud_provider(provider: ICloudProvider, /) -> None:
    global _provider
    _provider = provider


def reset_cloud_provider() -> None:
    global _provider
    _provider = None


def _resolve() -> ICloudProvider:
    discovered = {entry_point.name: entry_point for entry_point in entry_points(group=ENTRY_POINT_GROUP)}
    requested = os.getenv("CLOUD_PROVIDER")

    if requested is not None:
        if requested in BUILT_IN_PROVIDERS:
            return BUILT_IN_PROVIDERS[requested]
        if requested not in discovered:
            raise InfrastructureError(
                error_type=InfrastructureErrorType.ENVIRONMENT_ERROR,
                message=(
                    f"CLOUD_PROVIDER is {requested!r} but no provider is installed or built in under that "
                    f"name. Built in: {sorted(BUILT_IN_PROVIDERS)}. Installed: {sorted(discovered)}"
                ),
            )
        return _load(discovered[requested].load(), name=requested)

    if len(discovered) == 0:
        return BUILT_IN_PROVIDERS[DEFAULT_PROVIDER_NAME]

    if len(discovered) > 1:
        raise InfrastructureError(
            error_type=InfrastructureErrorType.ENVIRONMENT_ERROR,
            message=(
                f"More than one cloud provider is installed ({sorted(discovered)}). "
                "Set CLOUD_PROVIDER to say which one this process should use."
            ),
        )

    name, entry_point = next(iter(discovered.items()))
    return _load(entry_point.load(), name=name)


def _load(loaded: object, /, *, name: str) -> ICloudProvider:
    if not isinstance(loaded, ICloudProvider):
        raise InfrastructureError(
            error_type=InfrastructureErrorType.ENVIRONMENT_ERROR,
            message=f"The {name!r} entry point does not provide a cloud provider",
        )
    return loaded
