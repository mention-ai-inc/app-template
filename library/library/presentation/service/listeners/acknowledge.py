from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends

from library.application.ports.documents import DocumentID, IDocumentStore
from library.application.ports.eventbus import InboundEvent
from library.application.ports.transactions import ITransaction
from library.domain.commands.base import CommandID, CommandRead
from library.domain.events.base import EventPayload
from library.presentation.api.app import listener
from library.presentation.dependencies import get_message_parser
from library.providers.registry import get_cloud_provider


class AcknowledgeCommandResultPayload(EventPayload):
    command_id: str
    success: bool
    attempt: int = 1

    @classmethod
    def event_name(cls) -> str:
        return "AcknowledgeCommandResult"


def get_command_store() -> IDocumentStore[CommandRead, CommandID, ITransaction]:
    return get_cloud_provider().document_store(collection="commands", model=CommandRead, partition_key_type=CommandID)


@listener
async def acknowledge_command_result(
    message: Annotated[
        InboundEvent[AcknowledgeCommandResultPayload],
        Depends(get_message_parser(data_models=[AcknowledgeCommandResultPayload])),
    ],
    commands: IDocumentStore[CommandRead, CommandID, ITransaction] = Depends(get_command_store),
) -> None:
    document_id = DocumentID(message.data.command_id)
    await commands.field_set(document_id=document_id, field="success", value=message.data.success)
    await commands.field_set(document_id=document_id, field="processed_at", value=datetime.now(UTC))
    await commands.field_set(document_id=document_id, field="attempt_count", value=message.data.attempt)
