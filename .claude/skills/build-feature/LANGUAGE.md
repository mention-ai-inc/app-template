# Python backend

The backend is Python. `library/` is the kernel distribution (import root `library`) on top of the control plane (`control-plane/control_plane`); each service is `services/<svc>/` with package `<svc>_service`; migrations live in `backfills/`. Beside the layer-neutral rules, `aggregate-public-api`, `python-service-tests`, `llm-value-objects`, `presentation-dependency-factories` and the `*-python` companion rules apply.

## Domain

- Aggregates at `services/<svc>/<svc>_service/domain/aggregates/<name>/aggregate.py`, extending `Aggregate` from `library.domain.aggregates`, with `value_objects.py` beside them. Follow `aggregate-public-api`.
- Cross-service identifiers, events, and commands in `library/library/domain/value_objects/`, `events/`, and `commands/`.
- Domain services (stateless logic over several aggregates) in `domain/services/`; projections of another service's data in `domain/projections/`.
- `DomainError` comes from `control_plane.domain.errors`.
- Domain tests at `tests/domain/aggregates/test_<name>.py`.

## Domain interfaces

- Repository protocols in `domain/repositories.py`, extending `IRepository` from `library.domain.repositories`; `quick_get` is the non-transactional read for the hoisted-call shape in `unit-of-work-scope-python`.
- Capability protocols in `domain/interfaces/<name>.py`, one `Protocol` per capability, taking and returning domain value objects.

## Application

- Use cases at `application/<feature>/use_cases/<verb>.py`. DTOs in `application/<feature>/dtos.py`, the query service protocol in `queries.py`, application services under `application/<feature>/services/`.
- `add_log_context` from `control_plane.logs`.
- Tests at `tests/application/<feature>/use_cases/test_<verb>.py`, using stubs from `tests/stubs/` and the fakes in `library/library/_testutils/` and `control-plane/control_plane/_testutils/`. Follow `python-service-tests`.

## Infrastructure and presentation

- Persistence at `infrastructure/persistence/<name>.py`. Query services at `infrastructure/queries/<name>.py`.
- External services at `infrastructure/services/<name>/` with `service.py` and `models.py`. LLM-backed ones follow `llm-value-objects`.
- Dependency wiring in `presentation/dependencies/`: `repositories.py`, `queries.py`, `infrastructure_services.py`, and `use_cases/<feature>.py` with one `get_<verb>_use_case` per use case. Every factory returns the interface, never the class (`presentation-dependency-factories`).
- REST routes in `presentation/servers/rest/routers/<feature>/routes.py` with their models beside them, listeners in `presentation/listeners/`, executors in `presentation/executors/`, jobs in `presentation/jobs/`, pool modules under `presentation/pools/`.
- Commands are `[project.scripts]` entries in `services/<svc>/pyproject.toml`: `run-server-rest`, `run-pool-<name>`, `run-job-<name>`, `run-worker-<name>`.
- Route tests at `tests/presentation/servers/rest/routers/<feature>/test_routes.py`.

## Checks

- After editing `library/` or `control-plane/`, run `m update-local-dependencies` before any service test (`library-dependency-sync`).
- `m test-service-<svc>` and `m test-library` run the suites; `m run-checks-backend` runs pyright and ruff. Pyright must report 0 errors on every package touched, pre-existing ones included.
