## Read-after-write in Python unit-of-work blocks

The unit of work is `async with self._unit_of_work():`; reads go through the active transaction (`store.get(..., uow=self.uow)`), writes buffer on it.

Buggy — `get` and `save` interleaved in one loop:

```python
async with self._unit_of_work():
    for note_id, summary in summaries_by_id.items():
        note = previously_by_id.get(note_id)
        if note is None:
            note = await self._note_repository.get(note_id, organization_id=organization_id)  # READ
        note.record_summary(summary=summary)
        await self._note_repository.save(note, organization_id=organization_id)           # WRITE
        # next iteration's get() is now a read-after-write → runtime error
```

Fixed — all reads, then all writes:

```python
async with self._unit_of_work():
    note_updates: list[Note] = []
    for note_id, summary in summaries_by_id.items():
        note = previously_by_id.get(note_id)
        if note is None:
            note = await self._note_repository.get(note_id, organization_id=organization_id)  # READ phase
        note.record_summary(summary=summary)
        note_updates.append(note)

    for note in note_updates:                                                                 # WRITE phase
        await self._note_repository.save(note, organization_id=organization_id)
```

`Repository.quick_get(...)` is the non-transactional read (`store.get(document_id=...)` with no `uow`).

### Where the guard lives

`InMemoryRepository` (`library/library/_testutils/repository.py`) and the `local` provider's document store (`control-plane/control_plane/providers/local/documents.py`) raise `InfrastructureError(CLOUD_ERROR)` on a read after a write while a `FakeUnitOfWork` (`library/library/_testutils/unit_of_work.py`) block is open. A stub method that mirrors a production method backed by `quick_get` must call `self.quick_get(...)`, not `self.get(...)`; atomic-mutation stub methods touch `self._aggregates[(organization_id, aggregate_id)]` directly and bypass the guard, which is also correct.
