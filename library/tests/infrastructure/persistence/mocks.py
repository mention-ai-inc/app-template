from library.domain.entities import Entity
from library.domain.value_objects.core import (
    IDValueObject,
    IntegerValueObject,
    ModelValueObject,
)


class MainId(IDValueObject):
    PREFIX = "main_"


class StringSubId(IDValueObject):
    PREFIX = "ssub_"


class StringSub(Entity[StringSubId]):
    pass


class IntSubId(IntegerValueObject):
    pass


class IntSub(Entity[IntSubId]):
    pass


class CompositeSubId(ModelValueObject):
    org: str
    user: str


class CompositeSub(Entity[CompositeSubId]):
    pass


class MainEntity(Entity[MainId]):
    string_subs: list[StringSub] = []
    int_subs: list[IntSub] = []
    composite_subs: list[CompositeSub] = []


class SimpleEntity(Entity[MainId]):
    name: str = ""


class MockPartitionKey(IDValueObject):
    PREFIX = "tp_"
