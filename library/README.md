# Library

Shared kernel for acme services.

## Scope

`library/` is a shared kernel, not a place for service-specific logic. It should only contain:

- **Cross-service message contracts** — `domain/commands/*` and `domain/events/*`, plus any value object that is published as part of an event/command payload and consumed by more than one service.
- **DDD primitives shared by 2+ services** — value objects, interfaces, and domain errors that multiple services genuinely need (e.g. `domain/value_objects/{common,core,users,llm}`).
- **Shared infrastructure framework** — the request/response and messaging plumbing every service is built on: `presentation/api`, `presentation/auth`, `application/{ports,events}`, `infrastructure/{repository,unit_of_work,outbox,llm}`. The cloud behind those ports is an adapter under `library/providers/`, never an import here.

If a module only has one production consumer, it belongs in that service, not here. When in doubt, ask: would a second service ever import this? If the honest answer is no, move it out.

## Cross-service communication

Services never call each other's REST APIs synchronously. All cross-service communication goes through:

- **Commands and events** over the outbox (`domain/commands/*`, `domain/events/*`), or
- **Replication** — a service subscribes to another service's events and keeps its own local read replica.

Do not introduce synchronous HTTP calls between services to work around a missing data dependency; extend the async contract instead.
