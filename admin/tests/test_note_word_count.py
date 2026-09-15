import importlib
from collections.abc import Generator
from typing import Any

import pytest

from library._testutils.users_client import FakeUsersClient
from library.domain.value_objects.users import OrganizationID
from library.providers.local.database import LocalDatabase
from library.providers.local.provider import PROVIDER as LOCAL_PROVIDER
from library.providers.registry import reset_cloud_provider, set_cloud_provider

migration = importlib.import_module("admin.backfill.migrations.20260911_note_word_count")

ENVIRONMENT = "dev"
ORGANIZATION_ID = OrganizationID("org_1")
BODY = "Start with what went well."


@pytest.fixture(autouse=True)
def _on_the_local_provider() -> Generator[None]:  # pyright: ignore[reportUnusedFunction]
    set_cloud_provider(LOCAL_PROVIDER)
    LocalDatabase.clear()
    yield
    LocalDatabase.clear()
    reset_cloud_provider()


async def store_with(*, word_count: int | None) -> Any:
    store = migration.note_store(environment=ENVIRONMENT)
    note = migration.StoredNote(id=migration.StoredNoteId("note_1"), body=BODY, word_count=word_count)
    with store.connect_to_partition(ORGANIZATION_ID) as notes:
        await notes.set(document_id=notes.to_document_id(note.id), document_data=note)
    return store


async def stored_word_count(store: Any) -> int | None:
    with store.connect_to_partition(ORGANIZATION_ID) as notes:
        return (await notes.get(document_id=notes.to_document_id("note_1"))).word_count


async def migrate(store: Any, *, apply: bool) -> tuple[int, int]:
    return await migration.migrate_organization(store=store, organization_id=ORGANIZATION_ID, apply=apply)


async def test_a_note_without_a_word_count_is_stamped_from_its_body() -> None:
    store = await store_with(word_count=None)

    assert await migrate(store, apply=True) == (1, 0)
    assert await stored_word_count(store) == 5


async def test_a_note_that_already_carries_a_word_count_is_left_alone() -> None:
    store = await store_with(word_count=99)

    assert await migrate(store, apply=True) == (0, 1)
    assert await stored_word_count(store) == 99


async def test_a_dry_run_counts_the_work_without_writing_it() -> None:
    store = await store_with(word_count=None)

    assert await migrate(store, apply=False) == (1, 0)
    assert await stored_word_count(store) is None


async def test_every_organization_is_visited_when_none_is_named() -> None:
    users_client = FakeUsersClient.with_organization(organization_id=ORGANIZATION_ID)

    discovered = await migration.organization_ids_for(users_client=users_client, organization_id=None)

    assert discovered == [ORGANIZATION_ID]


async def test_a_named_organization_narrows_the_run_without_asking_the_identity_provider() -> None:
    users_client = FakeUsersClient()

    discovered = await migration.organization_ids_for(users_client=users_client, organization_id="org_2")

    assert discovered == [OrganizationID("org_2")]
