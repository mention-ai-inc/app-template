from collections.abc import Callable
from typing import Annotated, Any, Literal, Protocol, Self, get_args, get_origin

from fastapi.types import IncEx
from pydantic import BaseModel, ConfigDict

from library.domain.value_objects.core import (
    EnumValueObject,
    IDValueObject,
    IntegerValueObject,
    ModelValueObject,
    StringValueObject,
)


class IEntity[IdentityT: IDValueObject | ModelValueObject | StringValueObject | IntegerValueObject | EnumValueObject](
    Protocol
):
    id: IdentityT

    @classmethod
    def get_subentity_names(cls) -> list[str]: ...

    @classmethod
    def model_validate(
        cls,
        obj: Any,
        *,
        strict: bool | None = None,
        from_attributes: bool | None = None,
        context: Any | None = None,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> Self: ...

    def model_dump(
        self,
        *,
        mode: str | Literal["json", "python"] = "python",
        include: IncEx | None = None,
        exclude: IncEx | None = None,
        context: Any | None = None,
        by_alias: bool | None = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        round_trip: bool = False,
        warnings: bool | Literal["none", "warn", "error"] = True,
        fallback: Callable[[Any], Any] | None = None,
        serialize_as_any: bool = False,
    ) -> dict[str, Any]: ...


class Entity[IdentityT: IDValueObject | ModelValueObject | StringValueObject | IntegerValueObject | EnumValueObject](
    BaseModel
):
    model_config = ConfigDict(validate_assignment=True)

    id: IdentityT

    @classmethod
    def get_subentity_names(cls) -> list[str]:
        subentity_names: list[str] = []

        for field_name, field in cls.model_fields.items():
            if get_origin(field.annotation) is list and cls.__list_element_is_entity_subclass(
                get_args(field.annotation)[0]
            ):
                subentity_names.append(field_name)

        return subentity_names

    @classmethod
    def __list_element_is_entity_subclass(cls, element_type: Any) -> bool:
        origin = get_origin(element_type)
        if origin is Annotated:
            element_type = get_args(element_type)[0]
            origin = get_origin(element_type)

        if not isinstance(element_type, type):
            return False

        return issubclass(element_type, Entity)
