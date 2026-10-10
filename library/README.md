# Library

The Python product kernel for acme services. It depends on `control-plane`, which owns the ports,
the domain primitives, the audit model, the API scaffolding, and the provider registry; `library`
adds what a product backend in Python needs on top of that.

## Scope

`library/` is a shared kernel, not a place for service-specific logic. It should only contain:

- **Cross-service message contracts** — `domain/commands/*` and `domain/events/*`, plus any value
  object that is published as part of an event/command payload and consumed by more than one
  service.
- **DDD building blocks shared by 2+ services** — `domain/aggregates.py`, `domain/repositories.py`,
  `domain/services.py`, the audit classification and diff, and the value objects under
  `domain/value_objects/{llm,notes}`.
- **Shared infrastructure** — the outbox (`infrastructure/outbox.py`), the generic repository
  (`infrastructure/repository.py`), the LLM slice (`infrastructure/llm/`), the user-facing auth
  dependencies (`presentation/auth/`), the service listeners and triggers, and the `_testutils`
  fakes service suites build on. The cloud behind the ports is a provider under
  `control-plane/providers/`, never an import here.

If a module only has one production consumer, it belongs in that service, not here. When in doubt,
ask: would a second service ever import this? If the honest answer is no, move it out. If a module
would be identical for a TypeScript backend, it belongs in `control-plane`, not here.

## Cross-service communication

Services never call each other's REST APIs synchronously. All cross-service communication goes
through:

- **Commands and events** over the outbox (`domain/commands/*`, `domain/events/*`), or
- **Replication** — a service subscribes to another service's events and keeps its own local read
  replica.

Do not introduce synchronous HTTP calls between services to work around a missing data dependency;
extend the async contract instead.

## Stored document shapes

`control-plane/tests/fixtures/documents/` pins the shape of every document this kernel stores or
transmits. `tests/test_golden_documents.py` asserts the kernel still emits them byte-for-byte after
key sort; update the fixtures deliberately, never by regenerating them to make the test pass.
