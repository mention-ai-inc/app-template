# Add a service

Every `services/<name>` directory is one deployable domain service. Most of the tooling discovers
services by listing that directory, but a handful of places enumerate them by hand. Work through
this file top to bottom when creating a service; each section names the file, what to add, and how
to check it. Read `services/notes` first: it is the reference layout every section below assumes.

Sections 1 and 2 are written per backend language. The language branch supplies
`docs/add-service.language.md` with the same section numbers, and a generated product always has
it; this file names only what is the same for every language.

## 1. The package

Section 1 of `docs/add-service.language.md`: the package layout, its dependency manifest and
lockfile, its tests, and the executables it puts on `PATH` in the services image.

Whatever the language, the contract is the one in `services/README.md`: `run-server-rest`,
`run-pool-<name>`, `run-job-<name>` and `run-worker-<name>` for every component the service
declares, a `README.md` the image copies, and exactly three pools — `executors`, `listeners`,
`triggers` — where the listener pool includes the shared `acknowledge_command_result` listener and
the trigger pool is the kernel's, run unchanged.

## 2. The shared kernel

| File | What |
| --- | --- |
| `control-plane/control_plane/domain/value_objects/common.py` | Add the service to the `Service` enum. Aggregates and commands resolve their owning service from the `SERVICE` environment variable through this enum, and the test runner sets it from the directory name, so the value must equal the directory name. In the template this is a `main` edit. |
| `control-plane/control_plane/infrastructure/persistence/storage.py` | Add a `SERVICE_BUCKETS` entry only if the service reads or writes a bucket. |

Section 2 of `docs/add-service.language.md`: the ID value objects other services or surfaces will
reference, the event payloads the service publishes, and the command payloads it executes, in the
backend's kernel.

Follow `library-dependency-sync` after any `control-plane` or kernel change.

## 3. Repository tooling

| File | What |
| --- | --- |
| `pyproject.toml` (root) | Nothing: the ruff `src` globs already cover `services/*`. The type-checker environment for the new package is section 3 of `docs/add-service.language.md`. |
| `packages/acme-api/openapi.json`, `packages/acme-api/src/api.d.ts` | Nothing to edit: the language slot's generator discovers every `services/*` package, and `m compile-api` merges the service's REST routes into the contract and the client. Regenerate and commit both files as `docs/cloud-providers.md` describes; `m check-api-contract` fails until they match. |

The build, deploy, change-detection, and test scripts are generic. `m deploy-<name>` and
`m deploy-<name>-<type>-<component>` work as soon as Terraform knows the service, where
`<type>-<component>` is one of the service's deployable units: `server-rest`, `pool-<pool>`, or
`job-<name>`.

## 4. Terraform

Add the service to the `services` map in
`infrastructure/terraform/configurations/services/terraform.tfvars`. The map declares every
component: `servers`, `executor_pools` and the `executors` that name them, `listeners` with their
subscriptions, `jobs` with schedules, and the three `triggers` copied from the notes entry. Every
resource the branch creates for a service — its document indexes, its deployed components, its
command queues and its event subscriptions — is keyed on this map.

Components are created one per **pool**, not one per entrypoint. A service gets one deployed
component per entry in `executor_pools`, one for its listeners, and one for its triggers; each
executor, listener, and trigger is a route on the pool that hosts it. Band `executor_pools` by
runtime profile — a pool's `timeout_seconds` and `container_concurrency` apply to every command
routed to it, so give a command that needs a long timeout or a low concurrency its own pool rather
than widening a shared one. Each `executors` entry is still its own queue, so per-command rate
limits, retries, and backoff stay per command.

`m terraform-services` must apply before the first `m deploy-<name>`. The deploy script reads the
deployable components from Terraform output and refuses to run without them.

## 5. Production workflow

`.github/workflows/deployment.yaml` enumerates services by hand. Add a `workflow_dispatch` input
named after the service and a line in the "Deploy services to production" step that runs
`make -f infrastructure/cli/Makefile deploy-<name>` when the input is true.

## 6. Admin

Admin depends on `control-plane` alone and never imports a service package, so a new service needs
nothing here unless the feature-environment seed should populate it. The seed runs as a client of
the deployed API:

| File | What |
| --- | --- |
| `admin/admin/seed/phases/<name>.py` | A seed phase that writes through the service's REST routes with the `SeedClient`, registered in `admin/admin/seed/runner.py`. |
| `admin/admin/seed/auth.py`, `admin/admin/seed/clients.py` | Mint the impersonation token for the service that owns the seeded data; today that is `notes`. |

Backfills under `backfills/` go through the cloud provider's document store against a permissive
model of their own and need none of this.

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
m test-service-<name>
m compile-api
```

Then, on a feature branch with its environment created:

```
m terraform-services
m deploy-<name>
```

The service's OpenAPI spec is served at `/rest/<name>/openapi` on the feature environment API host
once the REST server is up. Each pool answers `GET /health` at its own deployed URL, which is the
quickest check that a pool came up and that its entrypoints all imported. The `verify` skill describes
what else can be checked without a browser session.
