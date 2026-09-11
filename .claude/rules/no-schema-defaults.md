---
paths:
  - "admin/admin/backfill/**/*.py"
  - "library/library/domain/**/*.py"
  - "services/*/*/domain/**/*.py"
---

## No default values on aggregates, entities, event payloads, or command payloads

Every field on an `Aggregate`, `Entity`, `ModelValueObject`, `EventPayload`, or `CommandPayload` is **required and has no default**. A default value is a lie the schema tells: it makes an absent field look like a present one, so a document that was never migrated deserializes as if it had been, and the bug surfaces later — as a silently wrong count, an empty list where data should be, a `None` that propagates into an LLM prompt — far from the change that caused it.

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

This also rules out the softer variants of the same shim: `Field(default=...)`, `Field(default_factory=...)`, `X | None = None` added purely so unmigrated data validates, and `model_config` / before-validators that fill in a missing key.

### Adding a field to an existing model → write a backfill

When a model already has documents in Firestore, adding a required field means **writing a backfill migration**, not defaulting the field.

1. Add the field as required on the model.
2. Add a date-prefixed migration under `admin/admin/backfill/migrations/` (e.g. `20260712_note_review_status.py`) exposing a module-level `BACKFILL = Backfill(name=..., description=..., run=...)`. `registry.discover()` picks it up automatically — migrations are data, not new CLI commands.
3. Migrations run **raw** against Firestore (`firestore.Client`, no service imports, no events) precisely because the new model rejects the old shape they are there to fix.
4. Support a dry run: `run(*, environment, apply, organization_id)`, writing only when `apply` is true, and print what was (or would be) rewritten.
5. Make it idempotent — skip documents that already carry the field, and mint any new IDs deterministically (`uuid5` over stable inputs) so partial runs and re-runs converge.

Run it with `m admin -- backfill list` / `m admin -- backfill run <name> [--apply] [--organization-id ...]`. **The backfill must run to completion in an environment before the new service code is deployed there** — it is a hard prerequisite, not a cleanup task.

`m admin -- backfill run` calls the admin API, which launches the
VPC-attached `${env}admin-j-backfill` Cloud Run job and polls it to completion — so backfills that
touch Redis work in every environment, including production (where the CLI also
requires `--confirm production`). The job runs the deployed admin image, so deploy it first —
`m deploy-admin` in a feature environment, or the **Deployment** workflow's `admin` input for
production — and run the backfill *before* the deployment that depends on it. See `admin/README.md`.

### Event and command payloads

Same rule, no backfill: payloads are messages, not stored records. A new field is required, and the publisher and consumer deploy together. Do **not** default a field so that in-flight or replayed old messages keep parsing — if a message shape has to change compatibly, that is a decision to raise explicitly, not to paper over with a default.

### The narrow exception

A default is fine only when it is part of the domain, not part of a migration:

- Identity and lifecycle plumbing on base classes (`id: EventID = Field(default_factory=lambda: EventID())`, `ttl`, `published_at`).
- A field whose absence is genuinely meaningful **from the model's first day** — `error: str | None`, `expires_at: datetime | None` — where `None` means "no error" / "never expires", not "we haven't backfilled this yet".

If you are reaching for a default because documents already exist without the field, that is the case this rule exists to stop. Write the backfill.
