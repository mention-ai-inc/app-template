# Review standards

Use this checklist selectively. Applicable project rules are authoritative.

## Application

- Use cases do not depend on other use cases.
- All reads precede writes inside `unit_of_work()`, including across loop iterations.
- External calls stay outside a unit of work where possible.
- Services never call each other synchronously. Cross-service work uses commands (`ICommandDispatcher`) and events (`IEventPublisher`) only; any REST, gRPC, or client call from one service to another is a must-fix, wherever it appears.
- Webhooks acknowledge quickly; LLM and retrieval work runs asynchronously.
- `add_log_context` records guard reasons, outcomes, identifiers once, and aggregate counts once. It never logs secrets, raw PII, LLM payloads, or per-item loop state.
- Extract an application service only when multiple callers need it.

## Domain

- Use a bare `status` enum for a simple lifecycle. Use a `state` value object only when status, timestamp, and error form one async-workflow snapshot.
- Aggregate, entity, event, and command fields have no schema defaults for backward compatibility; migrate stored data instead.
- Domain side effects use aggregate events and commands.

## Infrastructure and presentation

- LLM response models emit domain value objects directly and normalize through validators.
- `quick_get` is a deliberate non-transactional escape hatch, not a convenience.
- HTTP clients serve external APIs and OAuth, not internal orchestration.
- Routes, executors, listeners, and jobs stay thin and delegate to one use case.
- New executors, listeners, and triggers are registered in their pool module under `presentation/pools/`, under the name Terraform routes to.
- User-scoped cross-service calls use the established impersonation-token flow.

## Python tests

- Test paths mirror source paths; tests use `async def` without a decorator.
- Helpers and builders use double-underscore names and live at the bottom.
- Call records use `NamedTuple`; avoid `object`, broad `Any`, and dictionary-shaped records.
- Cross-service fakes live in `library/_testutils`; service-specific stubs live in `tests/stubs`.
- Query stubs do not share repository state, which would make tests tautological.
- Unit-of-work loops are tested with at least two aggregates.
- Assert state, events, commands, and fake calls as appropriate.
- Do not add type-ignore directives merely to make a test pass.

## Frontend

- Use project aliases, generated API types, and existing query or mutation hooks.
- Keep page-only components local and reusable components at the project component root.
- Do not add ad hoc query logic to pages.
- Review presentation against the agreed decisions in `docs/product/design.md`; do not enforce the scaffold's appearance or feedback patterns as product requirements.
- Check loading, empty, error, pending, disabled, and responsive states.
- Backend API changes regenerate clients with `m compile-api`.
- Mobile changes also follow the `mobile-frontend` skill.
- Web changes also follow the `web-frontend` skill.

## Comments

- Do not add explanatory or narrating code comments. Allow only required tool directives, shebangs, and equivalent machine-readable pragmas.

## Common severity

| Finding | Severity |
| --- | --- |
| Read-after-write, use-case dependency, unsafe synchronous handler work | Must fix |
| Synchronous service-to-service call (REST, gRPC, imported client) instead of a command or event | Must fix |
| Missing executor/listener pool registration or broken API contract | Must fix |
| Missing migration, risky test gap, tautological stub | Should fix |
| Redundant value-object conversion or minor naming drift | Nit |
