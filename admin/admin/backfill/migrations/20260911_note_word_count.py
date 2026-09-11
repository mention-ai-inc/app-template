"""Stamp `word_count` onto every stored note, computed from its body.

The example backfill: the shape every schema-change migration in this directory follows. A new
required field on `Note` means every existing `{env}notes_{org}_note` document must carry it before
the service that reads it deploys (see the `no-schema-defaults` rule).

Runs raw (a `firestore.Client`, no service imports, no events) and idempotent: documents already
carrying the field are skipped. Optional `organization_id` narrows the run; otherwise every
organization's note collection in the environment is discovered by collection name.
"""

from __future__ import annotations

from google.cloud import firestore

from admin.backfill.registry import Backfill
from admin.common.environment import project_for
from admin.common.options import verb

STAMPED_FIELD = "word_count"
COLLECTION_PREFIX = "notes_"
COLLECTION_SUFFIX = "_note"


def organization_ids_for(*, db: firestore.Client, environment: str, organization_id: str | None) -> list[str]:
    if organization_id is not None:
        return [organization_id]

    prefix = f"{environment}{COLLECTION_PREFIX}"
    return sorted(
        collection.id[len(prefix) : -len(COLLECTION_SUFFIX)]
        for collection in db.collections()
        if collection.id.startswith(prefix) and collection.id.endswith(COLLECTION_SUFFIX)
    )


def migrate_organization(
    *, db: firestore.Client, environment: str, organization_id: str, apply: bool
) -> tuple[int, int]:
    notes = db.collection(f"{environment}{COLLECTION_PREFIX}{organization_id}{COLLECTION_SUFFIX}")
    stamped_count = 0
    skipped_count = 0

    for document in notes.stream():
        data = document.to_dict() or {}
        if STAMPED_FIELD in data:
            skipped_count += 1
            continue

        stamped_count += 1
        if apply:
            document.reference.update({STAMPED_FIELD: len(data["body"].split())})

    return stamped_count, skipped_count


def backfill(*, environment: str, apply: bool, organization_id: str | None) -> None:
    db = firestore.Client(project=project_for(environment))
    stamped = verb(apply, done="Stamped", pending="Would stamp")

    for collection_organization_id in organization_ids_for(
        db=db, environment=environment, organization_id=organization_id
    ):
        stamped_count, skipped_count = migrate_organization(
            db=db, environment=environment, organization_id=collection_organization_id, apply=apply
        )
        print(
            f"{collection_organization_id}: {stamped} {STAMPED_FIELD} on {stamped_count} note(s) "
            f"({skipped_count} already stamped)."
        )


def _run(*, environment: str, apply: bool, organization_id: str | None = None) -> None:
    backfill(environment=environment, apply=apply, organization_id=organization_id)


BACKFILL = Backfill(
    name="note-word-count",
    description="Stamp word_count onto every stored note, computed from its body.",
    run=_run,
)
