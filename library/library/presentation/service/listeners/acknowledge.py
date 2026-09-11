from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends

from library.application.events import PubSubEvent
from library.domain.commands.base import CommandRead
from library.domain.events.base import EventPayload
from library.domain.value_objects.users import UserID
from library.infrastructure.persistence.firestore import DocumentID, Firestore
from library.presentation.api.app import listener
from library.presentation.api.runner import run
from library.presentation.dependencies import get_message_parser


class AcknowledgeCommandResultPayload(EventPayload):
    command_id: str
    success: bool
    attempt: int = 1

    @classmethod
    def pubsub_event_name(cls) -> str:
        return "AcknowledgeCommandResult"


def get_firestore() -> Firestore[CommandRead, UserID]:
    return Firestore(collection="commands", model=CommandRead, partition_key_type=UserID)


@listener
async def acknowledge_command_result(
    message: Annotated[
        PubSubEvent[AcknowledgeCommandResultPayload],
        Depends(get_message_parser(data_models=[AcknowledgeCommandResultPayload])),
    ],
    commands: Firestore[CommandRead, UserID] = Depends(get_firestore),
) -> None:
    document_id = DocumentID(message.data.command_id)
    await commands.field_set(document_id=document_id, field="success", value=message.data.success)
    await commands.field_set(document_id=document_id, field="processed_at", value=datetime.now(UTC))
    await commands.field_set(document_id=document_id, field="attempt_count", value=message.data.attempt)


def main() -> None:
    run(app=acknowledge_command_result)
