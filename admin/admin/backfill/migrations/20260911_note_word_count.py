"""Stamp `word_count` onto every stored note, computed from its body.

The example backfill: the shape every schema-change migration in this directory follows. A new
required field on `Note` means every existing `{env}notes_{org}_note` document must carry it before
the service that reads it deploys (see the `no-schema-defaults` rule).

Runs through the cloud provider's document store against a permissive local model, so it reads the
old document shape the real `Note` would reject, imports no service package, and emits no events.
Idempotent: documents already carrying the field are skipped. Optional `organization_id` narrows the
run; otherwise every organization known to the identity provider is visited.
"""

from __future__ import annotations

from typing import Any

from admin.backfill.registry import Backfill
from admin.common.options import run_async, verb
from library.application.ports.documents import IDocumentStore
from library.application.ports.users import IUsersClient
from library.domain.entities import Entity
from library.domain.value_objects.core import StringValueObject
from library.domain.value_objects.users import OrganizationID
from library.presentation.dependencies import get_users_client
from library.providers.registry import get_cloud_provider

STAMPED_FIELD = "word_count"
SERVICE_NAME = "notes"
COLLECTION_NAME = "note"


class StoredNoteId(StringValueObject):
    pass


class StoredNote(Entity[StoredNoteId]):
    body: str
    word_count: int | None = None


type NoteStore = IDocumentStore[StoredNote, OrganizationID, Any]


def note_store(*, environment: str) -> NoteStore:
    return get_cloud_provider().document_store(
        collection=COLLECTION_NAME,
        model=StoredNote,
        partition_key_type=OrganizationID,
        service=SERVICE_NAME,
        feature_environment=environment,
    )


async def organization_ids_for(*, users_client: IUsersClient, organization_id: str | None) -> list[OrganizationID]:
    if organization_id is not None:
        return [OrganizationID(organization_id)]

    organizations = await users_client.list_organizations()
    return sorted(organization.id for organization in organizations)


async def migrate_organization(*, store: NoteStore, organization_id: OrganizationID, apply: bool) -> tuple[int, int]:
    stamped_count = 0
    skipped_count = 0

    with store.connect_to_partition(organization_id) as notes:
        for note in (await notes.query()).entities:
            if note.word_count is not None:
                skipped_count += 1
                continue

            stamped_count += 1
            if apply:
                await notes.field_set(
                    document_id=notes.to_document_id(note.id), field=STAMPED_FIELD, value=len(note.body.split())
                )

    return stamped_count, skipped_count


async def backfill(*, environment: str, apply: bool, organization_id: str | None) -> None:
    store = note_store(environment=environment)
    stamped = verb(apply, done="Stamped", pending="Would stamp")

    for collection_organization_id in await organization_ids_for(
        users_client=get_users_client(), organization_id=organization_id
    ):
        stamped_count, skipped_count = await migrate_organization(
            store=store, organization_id=collection_organization_id, apply=apply
        )
        print(
            f"{collection_organization_id}: {stamped} {STAMPED_FIELD} on {stamped_count} note(s) "
            f"({skipped_count} already stamped)."
        )


def _run(*, environment: str, apply: bool, organization_id: str | None = None) -> None:
    run_async(backfill(environment=environment, apply=apply, organization_id=organization_id))


BACKFILL = Backfill(
    name="note-word-count",
    description="Stamp word_count onto every stored note, computed from its body.",
    run=_run,
)
