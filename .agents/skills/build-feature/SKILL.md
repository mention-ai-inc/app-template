---
name: build-feature
description: Turn a PRD or feature request into working code, layer by layer - domain model first with the developer confirming intent, then application use cases and queries, then infrastructure and presentation autonomously, then the web, mobile, or MCP surface. Use when starting a new feature, a new aggregate, or a new service from product requirements.
---

# Build a feature from requirements

The order is fixed: domain, application, infrastructure and presentation, surfaces. Each layer is finished, tested, and checked before the next starts. The only mandatory pause for human input is after the domain model. Everything after it follows from contracts the developer has already confirmed, so proceed without checking in unless a real ambiguity appears.

## 1. Read the requirements

- Read the PRD under `docs/product/prds/` and `docs/product/glossary.md`. Use glossary names for every object, field, and event.
- Read the PRDs it depends on. Their "Objects and contracts" sections say which aggregates and fields already exist or are promised.
- Read the smallest existing service end to end once. In the untouched scaffold that is `services/notes`, the reference implementation of every layer.
- Decide whether the feature lives in an existing service or needs a new one. A new service is warranted when the feature owns aggregates no existing service touches and has its own deployable components. Creating one follows `docs/add-service.md`.

## 2. Domain model, then stop and confirm

Write only `services/<svc>/<svc>_service/domain/` and the shared kernel pieces it needs, plus their tests.

- Aggregates at `domain/aggregates/<name>/aggregate.py` with `value_objects.py` beside them. Follow `aggregate-public-api`, `aggregate-state-vs-status`, and `no-schema-defaults`.
- Cross-service identifiers, events, and commands live in `library/library/domain/value_objects/`, `events/`, and `commands/`. Follow `library-dependency-sync`.
- Repository interfaces in `domain/repositories.py`. External capability interfaces as protocols in `domain/interfaces/`.
- Invariants raise `DomainError` with a `public_message` in learner-facing words. Side effects are events and commands added on the aggregate, never calls out.
- Domain tests at `tests/domain/aggregates/test_<name>.py` assert state, events, and commands.

Then present the model to the developer and ask before continuing. Cover, in this order:

1. The aggregates and their boundaries. Why each is one aggregate rather than two, and what is an entity or value object inside it.
2. Each lifecycle. The status values, which method moves between them, and what is refused.
3. The events and commands each transition emits, and who is expected to consume them.
4. Every PRD requirement or edge case that the model does not obviously cover, with a proposed answer.
5. Open questions the PRD deferred that the model had to decide.

Ask specific questions with a recommendation each. Do not ask the developer to review the code; ask whether the model matches their intent. Revise until they confirm. Record decisions that changed the PRD's meaning back into the PRD.

## 3. Application layer

Write `application/<feature>/` and its tests. No human checkpoint unless a use case needs a contract the domain model did not settle.

- One use case per entry point at `use_cases/<verb>.py`, constructor taking interfaces only. Follow `application-layer-dependencies` and `read-after-write`.
- Read models as DTOs in `dtos.py` and a query service protocol in `queries.py`. Queries never load aggregates.
- Extract an application service under `services/` only when two use cases need the same logic.
- Log with `add_log_context` as the `logging` rule describes.
- Tests at `tests/application/<feature>/use_cases/test_<verb>.py` using stubs from `tests/stubs/`. Follow `python-service-tests`.
- Run `m run-code-formatting`, then `m run-checks-backend`.

## 4. Infrastructure and presentation

Proceed autonomously. Everything here implements an interface that already exists.

- Persistence at `infrastructure/persistence/<name>.py` implementing the repository. Query services at `infrastructure/queries/<name>.py`.
- External services at `infrastructure/services/<name>/` with `service.py` and `models.py`. LLM-backed ones follow `llm-value-objects`.
- Dependency wiring in `presentation/dependencies/`: repositories, queries, infrastructure services, and one `get_<verb>_use_case` per use case.
- Entry points, each delegating to exactly one use case: REST routes in `presentation/servers/rest/routers/<feature>/`, listeners in `presentation/listeners/`, executors in `presentation/executors/`, jobs in `presentation/jobs/`.
- Register every new listener, executor, and job in the service's `pyproject.toml` scripts and in the Terraform `terraform.tfvars` for services.
- Route tests at `tests/presentation/servers/rest/routers/<feature>/test_routes.py`. Infrastructure service tests where behavior beyond pass-through exists.
- Run `m run-code-formatting`, `m run-checks-backend`, then `m compile-api` when routes changed.

## 5. Surfaces

Build only the surfaces the PRD names as in scope. Each has its own skill and conventions.

- Web: follow `web-frontend`. Hooks come from `packages/acme-api-client`, generated by `m compile-api`.
- Mobile: follow `mobile-frontend`.
- MCP: add tools under `apps/mcp/src/tools/` with tests beside them, calling the REST client in `apps/mcp/src/client.ts`.
- Run `m run-code-formatting`, then `m run-checks-frontend`.

## 6. Finish

- Walk the PRD's acceptance criteria and say which are met, which need a feature environment to confirm, and which were consciously left out.
- Run `m run-checks` before handing over.
- End with the deployment plan the `deployment-plan` rule requires, derived from the diff. A new listener or executor means `m terraform-services` runs after the service deploys.
