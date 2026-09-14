from datetime import UTC, datetime

from library.application.ports.unit_of_work import IUnitOfWork
from library.application.ports.users import IUsersClient
from library.logs import add_log_context
from notes_service.domain.aggregates.note.aggregate import Note
from notes_service.domain.repositories import INoteRepository


class PurgeNotesUseCase:
    SWEEP_LIMIT = 200

    def __init__(
        self,
        *,
        note_repository: INoteRepository,
        users_client: IUsersClient,
        unit_of_work: IUnitOfWork,
    ) -> None:
        self._note_repository = note_repository
        self._users_client = users_client
        self._unit_of_work = unit_of_work

    async def execute(self) -> None:
        cutoff = Note.purge_cutoff(as_of=datetime.now(UTC))
        num_purged_notes = 0

        organizations = await self._users_client.list_organizations()
        for organization in organizations:
            async with self._unit_of_work():
                expired_notes = await self._note_repository.list_created_before(
                    organization_id=organization.id, cutoff=cutoff, limit=self.SWEEP_LIMIT
                )
                for note in expired_notes:
                    await self._note_repository.delete(note.id, organization_id=organization.id)

            num_purged_notes += len(expired_notes)

        add_log_context(num_purged_notes=num_purged_notes)
