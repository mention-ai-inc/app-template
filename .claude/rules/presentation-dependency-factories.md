---
paths:
  - "services/*/*/presentation/**/*.py"
---

## Every FastAPI dependency is a `get_` factory that returns an interface

In a service's `presentation/dependencies/`, every dependency a route, executor, listener, or job receives is built by a module-level `get_<name>()` function. It returns the domain interface (`INoteRepository`, `ISummarizer`, `INoteQueryService`), never the concrete class, and routes and use-case factories annotate their parameters with that interface.

```python
# ❌ the class itself as the dependency
NoteRepositoryDependency = Annotated[NoteRepository, Depends(NoteRepository)]
SummarizerDependency = Annotated[Summarizer, Depends(Summarizer)]

# ✅ a factory, typed by the interface
def get_note_repository() -> INoteRepository:
    return NoteRepository()


def get_summarizer() -> ISummarizer:
    return Summarizer()
```

### Why

- **FastAPI reads the dependency's signature to build the request.** `Depends(SomeClass)` reads `SomeClass.__init__`. A class that inherits `object.__init__` exposes `*args, **kwargs`, which FastAPI turns into two required query parameters, and every request through it fails with a 422 that names neither the class nor the route. A factory's signature is exactly its parameters.
- **Presentation depends on the protocol.** The factory is the one place that names the concrete class, so swapping an implementation, or a fake in a test, touches one function.

### Rules

- Repositories go in `dependencies/repositories.py`, query services in `dependencies/queries.py`, infrastructure services in `dependencies/infrastructure_services.py`, use-case factories in `dependencies/use_cases/<feature>.py`. Each factory takes its own dependencies as `Annotated[..., Depends(get_...)]` parameters.
- A factory's return type is the interface. Name the concrete class only inside the factory body.
- Jobs and other non-FastAPI entry points call the same factories, passing dependencies explicitly.
- Never pass a class to `Depends(...)`. Control-plane helpers that are already functions (`get_unit_of_work`, `get_command_dispatcher`) are used as they are.

### Review checklist

- Does any `Depends(...)` receive a class rather than a function?
- Does any factory return a concrete infrastructure class where an interface exists?
