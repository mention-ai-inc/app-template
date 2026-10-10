## `state` vs `status` on aggregates

These are two distinct things in this codebase. Do not use them interchangeably.

### `status` — a single enum value

A bare `status` field holding one lifecycle enum is the right choice when the aggregate's lifecycle is a simple state machine and the only thing callers need to read is "what phase is this in?" Example: `Note.status`, a `NoteStatus`.

### `state` — a composite value object containing status + meta

A `<Name>State` model value object is only appropriate when the aggregate has an **async-write workflow** where callers need not just the current phase, but a snapshot of how the writer is progressing — typically `status`, a `last_*_at` timestamp, and an `error` field. Example: a `NoteSummaryState` carrying `status: NoteSummaryStatus`, `last_summarized_at: datetime | None` and `error: str | None`.

The aggregate exposes `aggregate.state.status`, and projections/queries (e.g. `state.status == COMPLETED`) and frontend polling (`untilStatus(d => d?.summary_state?.status, ...)`) read through the wrapper.

### Picking one

Default to a bare `status` enum. Only introduce a `State` value object when:

1. You need to expose multiple correlated fields (status + timestamp + error) together; **and**
2. Callers are likely to read them as a unit (e.g. a poll loop showing "writing… last refreshed at X, errored with Y").

If you only need `status`, do not wrap it in a `State` value object "for symmetry." A wrapper around one field is ceremony, and the wrapper changes the stored document shape (it nests under `state.`).

### Error and log messages must match the modeled field

If the aggregate exposes `status`, error/log copy says "status." If it exposes `state`, copy says "state." Do not write "Cannot do X in the current Y state" on an aggregate whose field is `status` — readers see `status` in the API and get misled. Match the wording to the model.

### Unrelated uses of "state" are fine

`state` as an OAuth/CSRF nonce, as a TanStack query field (`query.state`), or as English in LLM prompts ("State the substance plainly") is unrelated to this convention.
