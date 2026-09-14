from typing import Protocol, TypedDict


class OutboundMessage(TypedDict, total=False):
    data: str
    attributes: dict[str, str]


class IEventBus(Protocol):
    async def publish(self, *, topic_name: str, messages: list[OutboundMessage]) -> list[str]: ...
