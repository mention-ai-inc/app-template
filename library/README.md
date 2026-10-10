# Library

The product kernel: what every service in a product backend shares. This directory is a backend
language slot. On `main` it holds this README and the `providers/` slot; the language branch adds the
kernel package, its dependency manifest and lockfile, and its tests.

The kernel depends on `control-plane`, which owns the ports, the domain primitives, the audit model,
the API scaffolding and the provider registry, and is the same for every language. `library` adds
what a product backend needs on top of that, in the backend's language.

## Scope

`library/` is a shared kernel, not a place for service-specific logic. It should only contain:

- **Cross-service message contracts** — the commands and events, plus any value object that is
  published as part of a payload and consumed by more than one service.
- **DDD building blocks shared by 2+ services** — aggregates, repositories, domain services, the
  audit classification and diff, and shared value objects.
- **Shared infrastructure** — the outbox, the generic repository, the LLM slice, the user-facing
  auth dependencies, the service listeners and triggers, and the test fakes service suites build on.
  The cloud behind the ports is a provider under `control-plane/providers/`, never an import here.

If a module only has one production consumer, it belongs in that service, not here. When in doubt,
ask: would a second service ever import this? If the honest answer is no, move it out. If a module
would be identical for every backend language, it belongs in `control-plane`, not here.

## Cross-service communication

Services never call each other's REST APIs synchronously. All cross-service communication goes
through:

- **Commands and events** over the outbox, or
- **Replication** — a service subscribes to another service's events and keeps its own local read
  replica.

Do not introduce synchronous HTTP calls between services to work around a missing data dependency;
extend the async contract instead.

## Stored document shapes

`control-plane/tests/fixtures/documents/` pins the shape of every document a kernel stores or
transmits. Each language's kernel asserts it still emits them byte-for-byte after key sort; update
the fixtures deliberately, never by regenerating them to make a test pass.

## Python

`pyproject.toml` builds the `library` distribution (import root `library/`). Contracts live under
`library/domain/commands/*` and `library/domain/events/*`; shared building blocks under
`library/domain/`; shared infrastructure under `library/infrastructure/` and `library/presentation/`;
the golden-document test is `tests/test_golden_documents.py`. Services and `admin` install it as a
built copy, so run `m update-local-dependencies` after editing it (`.agents/rules/library-dependency-sync.md`).
