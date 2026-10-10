---
paths:
  - "backfills/backfills/**/*.py"
  - "control-plane/control_plane/domain/**/*.py"
  - "library/library/domain/**/*.py"
  - "services/*/*/domain/**/*.py"
---

## No schema defaults in Python models

The base classes are `Aggregate` (`library.domain.aggregates`), `Entity` and `ModelValueObject` (`control_plane.domain`), `EventPayload` (`control_plane.domain.events.base`) and `CommandPayload` (`library.domain.commands.base`). Their fields are pydantic fields, and every one of them is required:

```python
# ❌ default added so old documents keep parsing
class Note(Aggregate[NoteID, NoteEvent, NoteCommand]):
    title: NoteTitle
    review_status: ReviewStatus = ReviewStatus.UNREVIEWED
    related_ids: list[NoteID] = Field(default_factory=list)

# ✅ required — old documents are migrated to carry it
class Note(Aggregate[NoteID, NoteEvent, NoteCommand]):
    title: NoteTitle
    review_status: ReviewStatus
    related_ids: list[NoteID]
```

The softer variants are the same shim: `Field(default=...)`, `Field(default_factory=...)`, `X | None = None` added purely so unmigrated data validates, and `model_config` or `@model_validator(mode="before")` hooks that fill in a missing key.

### The backfill

A migration is a date-prefixed module under `backfills/backfills/migrations/` (e.g. `20260712_note_review_status.py`) exposing a module-level `BACKFILL = Backfill(name=..., description=..., run=...)` from `backfills.registry`; `registry.discover()` picks it up automatically. It reads and writes through `get_cloud_provider().document_store(...)` (`control_plane.providers.registry`) against a permissive `Entity` subclass declared in the migration itself, never through a service package. Its `run(*, environment, apply, organization_id)` writes only when `apply` is true, skips documents that already carry the field, and mints any new IDs with `uuid5` over stable inputs. `backfills/backfills/migrations/20260911_note_word_count.py` is the reference.

### The narrow exception

Identity and lifecycle plumbing on the base classes, such as `id: EventID = Field(default_factory=lambda: EventID())`, `ttl` and `published_at`, and fields whose `None` is meaningful from day one (`error: str | None`, `expires_at: datetime | None`).
