# Backend languages and cloud providers

This template ships one base branch and two axes of additions. `main` holds everything that depends
on neither a backend language nor a cloud; a `lang/*` branch adds the product backend in one
language; a `cloud/*` branch adds one cloud's infrastructure; and a leaf `<language>/<cloud>` is the
merge of `main` and one branch from each axis. Products are generated from leaves only.

```
main                               the base: apps, control plane, admin, m CLI, checks, product docs
 ├── lang/python                   main + the Python backend (library, services, backfills)
 ├── cloud/gcp                     main + GCP provider slots
 ├── cloud/aws                     main + AWS provider slots
 ├── cloud/azure                   main + Azure provider slots
 ├── python/gcp                    main + lang/python + cloud/gcp
 ├── python/aws                    main + lang/python + cloud/aws
 └── python/azure                  main + lang/python + cloud/azure
```

Python is the only backend language today; a TypeScript backend (`lang/ts`, leaves `ts/<cloud>`)
is the second one planned. The `m` CLI, `admin` and `control-plane` are Python on every branch
because they are tooling and operations, not product: a product developer on a non-Python leaf
never edits them.

To start a product, follow `docs/getting-started.md` and generate an independent `main` from a
leaf. The branch rules below apply only to this template, not to a generated product with a root
`project.json`.

## The invariant

1. **Every non-`main` branch differs from `main` by additions only.** A branch never edits a file
   `main` also has.
2. **`lang/*` and `cloud/*` add disjoint file sets**, so merging one of each into a leaf never
   conflicts.
3. **A leaf differs from the union of its parents by additions only**, and the only files a leaf
   may add are the ones that are both language- and cloud-specific. Today that is the TypeScript
   provider package (`library/providers/<cloud>/` on a `ts/<cloud>` leaf); Python leaves add
   nothing.
4. **Base owns every slot directory and its `README.md`.** A branch that needs different behaviour
   from a base file never edits it; it adds a hook on `main` that reads from a slot, and puts the
   behaviour in the slot.

Rule 1 is what keeps `git merge main` conflict-free forever. The moment both sides edit the same
file, every future sync conflicts on it and the branches drift apart for good.

Rule 4 is how `main` stays independently testable. Every base script that needs the backend or the
cloud looks for its hook and does nothing when the hook is absent, so `m run-checks`,
`m run-tests-backend`, `m check-api-contract`, `m run-web`, `m run-mobile` and the parity and PRD
targets all pass on `main` with nothing installed.

### Ownership

What each branch may add is checked, not just documented:

| Branch | May add |
| --- | --- |
| `lang/<l>` | `library/`, `services/`, `backfills/`, `infrastructure/cli/language/`, `infrastructure/docker/services/`, `infrastructure/docker/backfills/`, `.agents/rules.language.json`, rules under `.agents/rules/`, `.agents/skills/<skill>/LANGUAGE.md`, `docs/*.language.md`, and the generated `.claude/` and `.cursor/` mirrors of its guidance. |
| `cloud/<c>` | `infrastructure/terraform/`, `infrastructure/cli/provider/`, `infrastructure/docker/provider/`, `control-plane/providers/`, `.github/workflows/`, `.agents/rules.provider.json`, rules and skills under `.agents/`, anything under `docs/`, a root `PROVIDER.md`, a root ignore file, and the mirrors. |
| `<l>/<c>` | Nothing, except the language-and-cloud-specific package named in rule 3. |

Taking a file off `main` and onto a branch is the deletion-in-shared-ancestry sequence that
`docs/ports-and-adapters.md` section 6 records: commit A on `main` with the file present and
everything green, commit B on `main` deleting it, then `git checkout A -- <path>` on the branch.
The deletion is then in shared ancestry and every later merge of `main` is clean.

## Merge direction

`main` merges into `lang/*` and `cloud/*`; `main` and both parents merge into each leaf. Nothing
merges back.

```
m sync-branches
m check-branches
m check-branches -- --strict
```

`m sync-branches` merges `main` into every `lang/*` and `cloud/*` branch, then `main`, `lang/<l>`
and `cloud/<c>` into every leaf, checking the invariant after each merge. It refuses to run on a
dirty tree, a detached `HEAD`, or a generated product, and needs every branch of the topology to
exist locally. A conflict aborts that merge and stops the run; a merge that leaves a branch in
violation stops the run with the finding, leaving the merge in place because merging `main` is
always legitimate. It finishes on the branch it started from and prints one row per branch: how
many files the branch adds, what the sync did, and the result.

`m check-branches` runs the same checks without merging: every slot README exists on `main`; each
branch is additive-only against its merge base with `main` and adds nothing `main` has since gained;
each branch adds only what its axis owns; `lang/*` and `cloud/*` are pairwise disjoint; each leaf
adds exactly the union of its parents plus its leaf-only package; and each leaf's
`infrastructure/cli/language/project.json`, `infrastructure/cli/provider/project.json` and single
`control-plane/providers/<c>/pyproject.toml` name the language and cloud its branch name says.
`-- --strict` also requires every branch to contain the tip of `main` (and every leaf the tips of
its parents), which is what a release build needs. `-- --as <branch>` checks `HEAD` as if it were
that branch's tip, which is how `pull-request-checks.yaml` checks a pull request before it merges.

Work that belongs to every language and every cloud is committed on `main` and merged outward.
Work that belongs to one language or one cloud is committed on that branch and stays there. If you
find yourself wanting to merge a branch into `main`, what you actually have is base work committed
in the wrong place: move it.

## The language slots

Base owns each slot's directory and its `README.md`; the README states the contract. Everything
else under a slot comes from the language branch.

| Slot | Language branch provides |
| --- | --- |
| `library/` | The product kernel in that language: cross-service commands and events, shared building blocks, shared infrastructure, on top of `control-plane`. `library/providers/` inside it is the slot for TypeScript provider packages on `ts/<cloud>` leaves. |
| `services/<name>/` | One deployable service per directory, `notes` being the sample. Each puts `run-server-rest`, `run-pool-<name>`, `run-job-<name>` and `run-worker-<name>` on `PATH` in its image. |
| `backfills/` | The schema-change migrations and the `backfill` executable (`list --json`, `run <name> [--apply] [--organization-id <id>]`) that admin's backfill job runs. |
| `infrastructure/docker/services/Dockerfile`, `infrastructure/docker/backfills/Dockerfile` | The image recipes, each with its sibling `Dockerfile.dockerignore`. Build-arg `SERVICE` and the executables above are the contract the cloud branches build and deploy against. |
| `infrastructure/cli/language/` | `project.json` (`{"language": "<l>"}`), `targets.mk`, `envrc`, `init`, `create-virtual-environment`, `update-local-dependencies`, `run-checks`, `run-tests-backend`, `generate-openapi`, `service-components`, `helpers/`, and for Python `pyright.json`. Each is a hook a base script calls when present. |
| `.agents/rules.language.json` and the rules it names | Language-specific agent rules, including a `<rule>-python` companion for each mixed rule whose prose on `main` is language-neutral. `m sync-agent-parity` merges this manifest with `.agents/rules.json`; a rule named by two manifests is an error. |
| `.agents/skills/<skill>/LANGUAGE.md` | The language-specific supplement a skill reads first when it exists. |
| `docs/add-service.language.md`, `docs/remove-sample.language.md` | The language-specific sections of `docs/add-service.md` and `docs/remove-sample.md`. |

What `main` keeps of the backend, because it is the same for every language: `control-plane/`,
the Python kernel of ports, domain primitives, audit model, API scaffolding, provider registry and
`local` provider that `admin`, every provider and every backend build on; the golden stored-document
fixtures under `control-plane/tests/fixtures/documents/` that every kernel must emit and parse; and
the API contract described below.

## The cloud slots

| Slot | Cloud branch provides |
| --- | --- |
| `control-plane/providers/<cloud>/` | The provider package: one distribution exporting an `ICloudProvider` under the `acme.cloud_provider` entry point group, plus its conformance tests. The cloud's SDKs are its dependencies, never `control-plane`'s. |
| `infrastructure/terraform/` | All modules and configurations. Configuration names are the contract: `operations`, `services`, `web`, `mcp`, `admin`. |
| `infrastructure/cli/provider/targets.mk` | The deployment `m` targets, included by `infrastructure/cli/Makefile`. |
| `infrastructure/cli/provider/deployment/` | The scripts those targets run. |
| `infrastructure/cli/provider/helpers/` | Provider-specific helpers used only by those scripts. |
| `infrastructure/cli/provider/envrc` | Credentials, SDK on `PATH`, and any `PROVIDER_REQUIRED_PACKAGES`. Sourced by `.envrc`. |
| `infrastructure/cli/provider/feature-environment` | Maps `$FEATURE_ENVIRONMENT` onto a provider account or project. Sourced by `infrastructure/cli/_helpers/set-feature-environment`. |
| `infrastructure/cli/provider/project.json` | `{"cloud": "<c>", ...}`: nonsecret field mappings and read-only onboarding checks. |
| `infrastructure/cli/provider/pyright.json` | A partial pyright configuration for the provider package, merged like the language one. |
| `infrastructure/docker/provider/<component>/` | The build-and-push recipe for `services`, `mcp`, `admin`, and `backfills`. The `Dockerfile`s themselves are language or base files and stay out of it. |
| `.github/workflows/` | `deployment.yaml`, `create-feature-environment.yaml`, `destroy-feature-environment.yaml`, `pull-request-cloud-checks.yaml`. Base owns `pull-request-checks.yaml`, `mobile-deployment.yaml` and `template-release.yaml`. |
| `.agents/rules.provider.json` and the rules it names | Provider-specific agent rules, `deployment-plan.md` among them, merged by `m sync-agent-parity` like the language manifest. |
| `.agents/skills/` | `deploy-branch/` and `investigate-systems/`. Skills are discovered by directory, so no manifest edit is needed. |
| `docs/bootstrap.md` | Taking an empty account to a first deploy. |
| `docs/rename.provider.md` | The account, project or subscription ids this cloud names, and where they live. |
| `PROVIDER.md` | The branch's own checklist of what it adds and what is shaped differently. |
| Root ignore file | `.gcloudignore` or the provider's equivalent, when a build uploads a source context. |

### Required `m` targets

A cloud branch's `targets.mk` must define every target `AGENTS.md` and the `deployment-plan` rule
name, because the rest of the repository and the agent guidance assume they exist:

`deploy-<service>`, `deploy-admin`, `deploy-changes`, `deploy-web`, `deploy-mcp`,
`terraform-operations`, `terraform-services`, `terraform-mcp`, `terraform-admin`,
`create-feature-environment`, `destroy-feature-environment`, `clear-feature-environment`,
`list-feature-environments`, `ensure-feature-environment`, `build-service-<service>`, `build-admin`,
`build-backfills`, `list-cache-keys`, `terraform-plan-*`, `format-terraform`, and
`check-cloud-onboarding`.

On `main` these targets do not exist, and neither do the language ones (`test-library`,
`test-service-<name>`, `test-backfills`, `create-venv-<package>`). A leaf has both.

## Composing the hooks

Some base files cannot take additions by directory, so they compose from the slots instead:

| Base file | How the slots reach it |
| --- | --- |
| `infrastructure/cli/Makefile` | `-include`s `infrastructure/cli/provider/targets.mk` and `infrastructure/cli/language/targets.mk`. |
| `.envrc` | Sources `infrastructure/cli/provider/envrc` and `infrastructure/cli/language/envrc` when present; each appends to its `*_REQUIRED_PACKAGES` list. |
| `pyproject.toml` ruff | `src` globs already name `library`, `services/*`, `backfills` and `control-plane/providers/*`; a glob with nothing behind it is inert. |
| `pyproject.toml` pyright | `infrastructure/cli/_helpers/pyright_config.py` merges the root `[tool.pyright]` with the slots' `pyright.json` into the git-ignored `/pyrightconfig.json`; `m init` and the check scripts run it. |
| `pnpm-workspace.yaml`, `.npmrc` | The workspace globs name the backend directories; pnpm ignores a glob with no `package.json`, and `shared-workspace-lockfile=false` keeps every package's lockfile beside it. |
| `.gitignore`, `.dockerignore`, `osv-scanner.toml` | Nested beside the files they govern instead of edited at the root: per-Dockerfile `Dockerfile.dockerignore`, per-lockfile `osv-scanner.toml`. |
| `.agents/rules.json` | `rules.language.json` and `rules.provider.json` are merged in; overlap is an error. |
| `.agents/skills/*/SKILL.md` | Reads `LANGUAGE.md` beside it first, when it exists. |
| `docs/add-service.md`, `docs/remove-sample.md` | Their language-specific sections point at `docs/<doc>.language.md`. |

Adding a service still needs one `main` edit: the `Service` enum in
`control-plane/control_plane/domain/value_objects/common.py` (`docs/add-service.md` section 2).

## The API contract

`packages/acme-api/openapi.json` is the canonical API contract and `packages/acme-api/src/api.d.ts`
is the client compiled from it. Both are base files, committed on `main`, because every surface and
every backend language builds against the same contract. The generator that produces the contract
lives in the language slot (`infrastructure/cli/language/generate-openapi`), so `main` cannot
regenerate it on its own.

`m compile-api` runs the slot generator when it is installed and canonicalizes its output with
`infrastructure/cli/_helpers/canonicalize_openapi.py` into `openapi.json`; with or without a
language installed it then compiles `api.d.ts` from that file. `m check-api-contract` compiles both
into a temporary directory and fails on any difference: on `main` it proves `api.d.ts` matches
`openapi.json`, and on a language branch or leaf it also proves the backend matches the contract.
`pull-request-checks.yaml` runs it on every pull request.

To change the contract in this template:

1. Change the routes on the language branch (`lang/python`) and commit there.
2. Check out a leaf of that language (`python/gcp`), run `m init` and `m compile-api`.
3. Copy the regenerated `packages/acme-api/openapi.json` and `packages/acme-api/src/api.d.ts` to
   `main` and commit them there; discard the leaf's working-tree copy.
4. Run `m sync-branches`.

In a generated product `main` carries the backend, so `m compile-api` just regenerates the two files
in place and the product's pull-request checks keep them honest.

## Standalone releases

Standalone launcher releases are built on `main` after `m sync-branches`, and
`m check-branches -- --strict` is the gate: every branch must contain the release commit and differ
from it by additions only. `m test-template-launcher` tests the package and
`m build-template-release` produces the wheel, source distribution, and one pinned archive per leaf.
See `docs/template-releases.md`. The shared `.github/workflows/template-release.yaml` is excluded
from generated products.

## The ports

`control-plane/control_plane/application/ports/` states everything the base needs from a cloud,
and nothing more. Each port is a `typing.Protocol`; each cloud branch ships one package that
satisfies all of them. `main` itself is satisfied by the built-in `local` provider under
`control-plane/control_plane/providers/local/`, which is what keeps the ports honest — a port no
second implementation can meet is a port that has leaked its first cloud's semantics. The
conformance suite under `control-plane/tests/application/ports/conformance/` holds every provider
to the same contract and is the definition of done for a new cloud.

| Port | local | GCP | AWS | Azure |
| --- | --- | --- | --- | --- |
| `IDocumentStore` | in-memory dict | Firestore | DynamoDB | Cosmos DB NoSQL |
| `ITransaction` | `LocalTransaction` | Firestore transaction | `TransactWriteItems` | transactional batch |
| `IDocumentChangeFeed` | request body | Eventarc trigger | Streams via EventBridge Pipes | change feed with leases |
| `IEventBus` | in-process list | Pub/Sub topic | SNS topic to SQS | Service Bus topic |
| `ITaskQueue` | in-process list | Cloud Tasks | SQS queue | Service Bus queue |
| `IBlobStore` | in-memory dict | Cloud Storage | S3 | Blob Storage |
| `ISecretStore` | environment | Secret Manager | Secrets Manager | Key Vault secrets |
| `IIdentity` | unsigned token | IAM `signJwt` | KMS asymmetric sign | Key Vault keys |
| `IRuntimeContext` | environment | project metadata | STS caller identity | subscription settings |
| `IPoolDriver` | none | none | `SqsPoolDriver` | `AzurePoolDriver` |
| `IJobRunner` | in-process task | Cloud Run job | ECS `RunTask` | Container Apps job |
| `ILogReader` | captured log records | Cloud Logging | CloudWatch Logs | Log Analytics |
| `IOperatorAuth` | a header | IAP assertion | ALB OIDC data | built-in auth principal |

`IAsyncCache` is the exception that proves the shape: Redis is portable, so `main` owns the only
implementation and a cloud branch supplies nothing but `REDIS_HOST`, `REDIS_PORT`, and `REDIS_TLS`.

`IPoolDriver` is where the clouds differ most. GCP pushes work over HTTP — Pub/Sub and Cloud Tasks
both deliver into Cloud Run — so a pool is an ordinary server and the port returns `None`, exactly as
it does locally. AWS and Azure have no push delivery, so their drivers long-poll the queue and
dispatch into the application's own routes. Everything above `run_pool()` is unaware of which it got.

The ports are the same for every backend language. A Python backend calls them through
`control-plane` directly; a TypeScript backend reimplements the same protocols and holds its
providers to the same conformance suite, which is why the port surface is kept this narrow.

The Terraform estates line up the same way, though nothing in the base depends on them:

| | GCP | AWS | Azure |
| --- | --- | --- | --- |
| Compute | Cloud Run | ECS Fargate | Container Apps |
| Registry | Artifact Registry | ECR | ACR |
| Edge | Load balancer, Certificate Manager, Cloud Armor | ALB, ACM, WAFv2 | Front Door |
| DNS | Cloud DNS | Route 53 | Azure DNS |
| Network | Shared VPC, Cloud NAT | VPC, NAT gateway, endpoints | Container App environment |
| CI identity | Workload identity federation | IAM OIDC role | Entra federated credentials |
| Observability | Logging sink, Monitoring, BigQuery | CloudWatch alarms, Glue | Log Analytics, Monitor |

The web app deploys to Vercel from every branch.

## Choosing a provider

`control-plane/control_plane/providers/registry.py` resolves the provider once per process from the
`acme.cloud_provider` entry point group. No distribution installed means `local`. Exactly one means
that one, with no configuration. More than one is an error rather than a guess, and `CLOUD_PROVIDER`
says which to use — set it in CI, where a branch may install a second provider to test against.

A cloud branch therefore needs no `CLOUD_PROVIDER` anywhere in its estate: installing its own
provider package is the whole of the configuration. Every environment that installs Python loops
over `control-plane/providers/*/pyproject.toml` and installs what it finds, which is nothing on
`main` and exactly one provider on a cloud branch or leaf.

## The control plane

`admin` runs the same three ports on every cloud: it starts a job, polls the execution, reads the
execution's logs, and identifies the operator whichever gate fronts it.

That gate is the one place the clouds cannot be made to look alike, so the port absorbs it. Each
cloud terminates the login at the edge and hands the application a header — IAP's signed assertion,
the load balancer's `x-amzn-oidc-data`, the container app's `X-MS-CLIENT-PRINCIPAL` — and the
adapter's whole job is to turn that header into an `Operator`. The staff allowlist and the audit
actor stay on `main`, because they are the same everywhere.

The deployed API is for people. No cloud's gate admits a machine, so `m admin` does not call it: the
CLI resolves the same ports and launches the job itself, with the operator's own cloud credentials.
That is why `IOperatorAuth` also answers `caller_identity()` — a CLI-launched run writes its own
audit record, and it should name whoever actually ran it.

`admin` depends on `control-plane` alone and never imports a service or the language kernel. Its
backfill commands launch the language slot's `backfills` image and read the catalogue out of the
job's logs, so the same admin serves a Python backend and a TypeScript one.
