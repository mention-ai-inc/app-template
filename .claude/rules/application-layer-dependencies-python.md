---
paths:
  - "services/*/*/application/**/*.py"
  - "services/*/tests/application/**/*.py"
---

## Application-layer dependencies in Python services

Use cases live at `services/<svc>/<svc>_service/application/<feature>/use_cases/<verb>.py`; application services at `services/<svc>/<svc>_service/application/<feature>/services/<name>.py`.

The red flag is a constructor parameter typed as another use case:

```python
class BatchWriteUseCase:
    def __init__(self, *, write_use_case: WriteUseCase) -> None:  # ❌ never correct
        ...
```

An application service has the same constructor shape as a use case and owns its own `async with self._unit_of_work():` block:

```python
class NoteSummarizer:
    def __init__(self, *, note_repository: INoteRepository, summarizer: ISummarizer, unit_of_work: IUnitOfWork) -> None:
        ...

    async def summarize(self, *, note_id: NoteID, organization_id: OrganizationID) -> None:
        async with self._unit_of_work():
            ...
```

In tests, a `__build_use_case(...)` helper that instantiates one use case to feed another is the same dependency in disguise and means it has to go.
