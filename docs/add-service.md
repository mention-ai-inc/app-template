# Add a service

Every `services/<name>` directory is one deployable domain service. Most of the tooling discovers
services by listing that directory, but a handful of places enumerate them by hand. Work through
this file top to bottom when creating a service; each section names the file, what to add, and how
to check it. Read `services/notes` first: it is the reference layout every section below assumes.

## 1. The package

Create `services/<name>/` with `pyproject.toml`, `README.md`, `<name>_service/`, and `tests/`.

- `pyproject.toml`: project name `<name>-service`, dependency on `library` via the path source, the
  dev group and pytest settings from `services/notes/pyproject.toml`, and a `[project.scripts]`
  entry for every server, pool, and job. A service has exactly three pool scripts —
  `run-pool-executors`, `run-pool-listeners`, `run-pool-triggers` — and the trigger one points at
  `library.presentation.service.triggers.pool:main`, which every service runs unchanged.
- `<name>_service/presentation/pools/` holds `executors.py` and `listeners.py`, each mapping the name
  Terraform routes to onto the handler that serves it. The listener pool includes the shared
  `acknowledge_command_result` listener; every service runs it.
- `README.md` must exist. The services Dockerfile copies it.
- The package is `<name>_service`, laid out as `domain/`, `application/`, `infrastructure/`,
  `presentation/`. The `build-feature` skill fills these in.
- `tests/` mirrors the package, with `conftest.py` and `stubs/`.

`m init` loops over `services/*`, creates the virtual environment, and writes `uv.lock`. The
Dockerfile builds with `--frozen`, so commit the lock.

## 2. The shared kernel

| File | What |
| --- | --- |
| `library/library/domain/value_objects/common.py` | Add the service to the `Service` enum. Aggregates and commands resolve their owning service from the `SERVICE` environment variable through this enum, and the test runner sets it from the directory name, so the value must equal the directory name. |
| `library/library/domain/value_objects/<name>.py` | ID value objects other services or surfaces will reference. |
| `library/library/domain/events/<name>.py` | Event payloads the service publishes. |
| `library/library/domain/commands/<name>.py` | Command payloads the service executes, each with `SERVICE: ClassVar[Service]` set to the new member. |
| `library/library/infrastructure/persistence/storage.py` | Add a `SERVICE_BUCKETS` entry only if the service reads or writes a bucket. |

Follow `library-dependency-sync` after any library change.

## 3. Repository tooling

| File | What |
| --- | --- |
| `pyproject.toml` (root) | Add `<name>_service` to `known-first-party`. Add a pyright execution environment for `services/<name>` and add the service's site-packages and root to the `infrastructure/cli/_helpers` environment. |
| `infrastructure/cli/_helpers/generate_openapi.py` | Add the service to `SERVICES` so `m compile-api` merges its REST routes into the unified spec and the generated client. |

The build, deploy, change-detection, and test scripts are generic. `m deploy-<name>` and
`m deploy-<name>-<type>-<component>` work as soon as Terraform knows the service, where
`<type>-<component>` is one of the service's deployable units: `server-rest`, `pool-<pool>`, or
`job-<name>`.

## 4. Terraform

Add the service to the `services` map in
`infrastructure/terraform/configurations/services/terraform.tfvars`. The map declares every
component: `servers`, `executor_pools` and the `executors` that name them, `listeners` with their
subscriptions, `jobs` with schedules, and the three `triggers` copied from the notes entry. Firestore
indexes, the Cloud Run services, the Cloud Tasks queues, and the Pub/Sub subscriptions are all keyed
on this map.

Cloud Run services are created one per **pool**, not one per entrypoint. A service gets one Cloud Run
service per entry in `executor_pools`, one for its listeners, and one for its triggers; each executor,
listener, and trigger is a route on the pool that hosts it. Band `executor_pools` by runtime profile —
a pool's `timeout_seconds` and `container_concurrency` apply to every command routed to it, so give a
command that needs a long timeout or a low concurrency its own pool rather than widening a shared one.
Each `executors` entry is still its own Cloud Tasks queue, so per-command rate limits, retries, and
backoff stay per command.

`m terraform-services` must apply before the first `m deploy-<name>`. The deploy script reads the
deployable components from Terraform output and refuses to run without them.

## 5. Production workflow

`.github/workflows/deployment.yaml` enumerates services by hand. Add a `workflow_dispatch` input
named after the service and a line in the "Deploy services to production" step that runs
`make -f infrastructure/cli/Makefile deploy-<name>` when the input is true.

## 6. Admin

Only when the admin control plane must import the service's package, for seeding through its API
or for a backfill that needs its models:

| File | What |
| --- | --- |
| `admin/pyproject.toml` | Add `<name>_service` to dependencies and to `[tool.uv.sources]`. |
| `infrastructure/docker/admin/Dockerfile` | Add the service to the `COPY` of `pyproject.toml`, to the `for service in ...` loop, and to the final `COPY` of the package. |
| `admin/admin/seed/phases/<name>.py` | A seed phase, registered in `admin/admin/seed/runner.py`. |

Raw backfills under `admin/admin/backfill/migrations/` go through the cloud provider's document
store against a permissive model of their own and need none of this.

## 7. Surfaces

Routes appear in the generated client after `m compile-api`. Query hooks and keys live in
`packages/acme-api-client/src/`, web routes under `apps/web/src/routes/`, mobile screens under
`apps/mobile/app/`, and MCP tools under `apps/mcp/src/tools/` registered in `tools/index.ts`. The
`build-feature`, `web-frontend`, and `mobile-frontend` skills cover these.

## 8. Verify

```
m init
m run-code-formatting
m run-checks
m compile-api
```

Then, on a feature branch with its environment created:

```
m terraform-services
m deploy-<name>
```

The service's OpenAPI spec is served at `/rest/<name>/openapi` on the feature environment API host
once the REST server is up. Each pool answers `GET /health` at its own Cloud Run URL, which is the
quickest check that a pool came up and that its entrypoints all imported. The `verify` skill describes
what else can be checked without a browser session.
