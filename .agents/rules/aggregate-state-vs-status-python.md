## `state` vs `status` in Python aggregates

`status` is a bare enum field on the aggregate:

```python
class Note(Aggregate[NoteID, NoteEvent, NoteCommand]):
    status: NoteStatus
```

`state` is a `ModelValueObject` subclass (`control_plane.domain.value_objects.core`) wrapping the status and its meta, stored nested under `state.`:

```python
class NoteSummaryState(ModelValueObject):
    status: NoteSummaryStatus
    last_summarized_at: datetime | None
    error: str | None
```

The aggregate exposes `aggregate.state.status`, and queries compare `state.status == NoteSummaryStatus.COMPLETED`. The reference aggregate is `services/notes/notes_service/domain/aggregates/note/aggregate.py`.
