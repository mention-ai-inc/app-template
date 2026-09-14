from datetime import UTC, datetime, timedelta

from library._testutils.unit_of_work import FakeUnitOfWork
from library._testutils.users_client import FakeUsersClient
from library.application.ports.users import Organization
from library.domain.value_objects.users import (
    OrganizationID,
    OrganizationPrivateMetadata,
    OrganizationPublicMetadata,
    UserID,
)
from notes_service.application.notes.use_cases.purge import PurgeNotesUseCase
from notes_service.domain.aggregates.note.aggregate import Note
from notes_service.domain.aggregates.note.value_objects import NoteBody, NoteTitle
from tests.stubs.repositories import InMemoryNoteRepository


async def test_purge_deletes_expired_notes_across_organizations() -> None:
    org_a = OrganizationID("org_a")
    org_b = OrganizationID("org_b")
    note_repository = InMemoryNoteRepository()
    expired_a = __make_note(organization_id=org_a, age=Note.RETENTION + timedelta(days=1))
    expired_b = __make_note(organization_id=org_b, age=Note.RETENTION + timedelta(days=1))
    await note_repository.seed(expired_a, organization_id=org_a)
    await note_repository.seed(expired_b, organization_id=org_b)
    use_case = __build_use_case(note_repository=note_repository, organization_ids=[org_a, org_b])

    await use_case.execute()

    assert await note_repository.exists(expired_a.id, organization_id=org_a) is False
    assert await note_repository.exists(expired_b.id, organization_id=org_b) is False


async def test_purge_keeps_notes_younger_than_retention() -> None:
    note_repository = InMemoryNoteRepository()
    fresh = __make_note(organization_id=__org(), age=Note.RETENTION - timedelta(days=1))
    await note_repository.seed(fresh, organization_id=__org())
    use_case = __build_use_case(note_repository=note_repository, organization_ids=[__org()])

    await use_case.execute()

    assert await note_repository.exists(fresh.id, organization_id=__org()) is True


async def test_purge_deletes_multiple_notes_in_one_unit_of_work() -> None:
    note_repository = InMemoryNoteRepository()
    expired_1 = __make_note(organization_id=__org(), age=Note.RETENTION + timedelta(days=1))
    expired_2 = __make_note(organization_id=__org(), age=Note.RETENTION + timedelta(days=2))
    await note_repository.seed(expired_1, organization_id=__org())
    await note_repository.seed(expired_2, organization_id=__org())
    unit_of_work = FakeUnitOfWork()
    use_case = __build_use_case(note_repository=note_repository, organization_ids=[__org()], unit_of_work=unit_of_work)

    await use_case.execute()

    assert unit_of_work.enter_count == 1
    assert await note_repository.list_ids(organization_id=__org()) == []


def __build_use_case(
    *,
    note_repository: InMemoryNoteRepository,
    organization_ids: list[OrganizationID],
    unit_of_work: FakeUnitOfWork | None = None,
) -> PurgeNotesUseCase:
    return PurgeNotesUseCase(
        note_repository=note_repository,
        users_client=FakeUsersClient(
            organizations={organization_id: __organization(organization_id) for organization_id in organization_ids}
        ),
        unit_of_work=unit_of_work or FakeUnitOfWork(),
    )


def __org() -> OrganizationID:
    return OrganizationID("org_1")


def __organization(organization_id: OrganizationID) -> Organization:
    return Organization(
        id=organization_id,
        name=organization_id,
        slug=organization_id,
        max_allowed_memberships=1,
        public_metadata=OrganizationPublicMetadata(),
        private_metadata=OrganizationPrivateMetadata(),
    )


def __make_note(*, organization_id: OrganizationID, age: timedelta) -> Note:
    note = Note.create(
        organization_id=organization_id,
        author_id=UserID("user_1"),
        title=NoteTitle("Release plan"),
        body=NoteBody("Ship on Tuesday."),
    )
    note.created_at = datetime.now(UTC) - age
    return note
