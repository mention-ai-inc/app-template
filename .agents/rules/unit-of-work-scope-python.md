## Unit-of-work scope in Python services

The unit of work is `async with self._unit_of_work():`, a transaction on the control plane's document store. The shape for work that needs slow input reads outside the block, makes the call, then re-reads inside:

```python
note = await self._note_repository.quick_get(note_id, organization_id=organization_id)
summary = await self._summarizer.summarize(organization_id=organization_id, title=note.title, body=note.body)

async with self._unit_of_work():
    note = await self._note_repository.get(note_id, organization_id=organization_id)
    note.record_summary(summary=summary)
    await self._note_repository.save(note)
```

`Note.record_summary` decides whether the summary still applies; the use case only re-reads and applies.

Red flags, never correct:

- An `await` on an `infrastructure/services/<name>/` client, an `ISummarizer`-style domain interface, or an `httpx` call inside the block.
- Two repositories' `save` calls in one block, unless both save the same aggregate type from a single input.
- A listener in `presentation/listeners/` whose use case calls `get_all` or a `list_*` query and saves each result; that is a command for an executor in `presentation/executors/` on its own pool.
- A `save` inside the block of an aggregate that was read before the block opened, without a `get` in between.

`InMemoryRepository` and `FakeUnitOfWork` from `library/library/_testutils/` enforce read-before-write but not block scope; the second aggregate type in a block and the slow call inside it are caught only by review.
