# Cloud providers

This template ships one cloud-agnostic trunk and one branch per cloud. `main` holds everything that
does not depend on a provider; `cloud/gcp`, `cloud/aws`, and `cloud/azure` each add the provider's
infrastructure on top of it and nothing else.

```
main                      the base: apps, library, services, checks, product docs
 ├── cloud/gcp            main + GCP provider slots
 ├── cloud/aws            main + AWS provider slots
 └── cloud/azure          main + Azure provider slots
```

Clone `main` to work on the product. Clone a `cloud/*` branch to get a repository you can deploy.

## The one rule

**Every difference between `main` and a `cloud/*` branch is a file that exists on the cloud branch
and does not exist on `main`.** A cloud branch never edits a file that `main` also has.

That is what keeps `git merge main` conflict-free forever. The moment both sides edit the same file,
every future sync conflicts on it, and the branches drift apart for good. If a cloud branch needs
different behaviour from a file on `main`, the fix is never to edit it there — it is to add a hook on
`main` that reads from a provider slot, and put the behaviour in the slot.

## Merge direction

`main` merges **into** the cloud branches. Nothing merges back.

```
git switch cloud/gcp && git merge main
```

Work that belongs to every cloud is committed on `main` and merged outward. Work that belongs to one
cloud is committed on that cloud's branch and stays there. If you find yourself wanting to merge a
cloud branch into `main`, what you actually have is base work committed in the wrong place: move it.

## The slots

Base owns each slot's directory and its `README.md`. Everything else under a slot comes from the
cloud branch.

| Slot | Cloud branch provides |
| --- | --- |
| `library/providers/<cloud>/` | The provider package: one distribution exporting an `ICloudProvider` under the `acme.cloud_provider` entry point group, plus its conformance tests. The cloud's SDKs are its dependencies, never `library`'s. |
| `infrastructure/terraform/` | All modules and configurations. Configuration names are the contract: `operations`, `services`, `web`, `mcp`, `admin`. |
| `infrastructure/cli/provider/targets.mk` | The deployment `m` targets, included by `infrastructure/cli/Makefile`. |
| `infrastructure/cli/provider/deployment/` | The scripts those targets run. |
| `infrastructure/cli/provider/helpers/` | Provider-specific helpers used only by those scripts. |
| `infrastructure/cli/provider/envrc` | Credentials, SDK on `PATH`, and any `PROVIDER_REQUIRED_PACKAGES`. Sourced by `.envrc`. |
| `infrastructure/cli/provider/feature-environment` | Maps `$FEATURE_ENVIRONMENT` onto a provider account or project. Sourced by `infrastructure/cli/_helpers/set-feature-environment`. |
| `infrastructure/docker/provider/<component>/` | The image build recipe for `services`, `mcp`, and `admin`. The `Dockerfile`s themselves are portable and stay on `main`. |
| `.github/workflows/` | `deployment.yaml`, `create-feature-environment.yaml`, `destroy-feature-environment.yaml`, `pull-request-cloud-checks.yaml`. Base owns `pull-request-checks.yaml` and `mobile-deployment.yaml`. |
| `.agents/rules.provider.json` and the rules it names | Provider-specific agent rules, `deployment-plan.md` among them. `m sync-agent-parity` merges this manifest with `.agents/rules.json`. |
| `.agents/skills/` | `deploy-branch/` and `investigate-systems/`. Skills are discovered by directory, so no manifest edit is needed. |
| `docs/bootstrap.md` | Taking an empty account to a first deploy. |
| Root ignore file | `.gcloudignore` or the provider's equivalent. |

### Required `m` targets

A cloud branch's `targets.mk` must define every target `AGENTS.md` and the `deployment-plan` rule
name, because the rest of the repository and the agent guidance assume they exist:

`deploy-<service>`, `deploy-admin`, `deploy-changes`, `deploy-web`, `deploy-mcp`,
`terraform-operations`, `terraform-services`, `terraform-mcp`, `terraform-admin`,
`create-feature-environment`, `destroy-feature-environment`, `clear-feature-environment`,
`list-feature-environments`, `ensure-feature-environment`, `build-service-<service>`, `build-admin`,
`list-cache-keys`.

On `main` these targets do not exist. `m run-checks`, `m run-checks-backend`,
`m run-checks-frontend`, the test targets, `m compile-api`, `m run-web`, `m run-mobile`, and the
parity and PRD targets all work on `main` and are the reason base stays independently testable.

## The ports

`library/library/application/ports/` states everything the base needs from a cloud, and nothing more.
Each port is a `typing.Protocol`; each cloud branch ships one package that satisfies all of them.
`main` itself is satisfied by the built-in `local` provider, which is what keeps the ports honest — a
port no second implementation can meet is a port that has leaked its first cloud's semantics.

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

`library/library/providers/registry.py` resolves the provider once per process from the
`acme.cloud_provider` entry point group. No distribution installed means `local`. Exactly one means
that one, with no configuration. More than one is an error rather than a guess, and `CLOUD_PROVIDER`
says which to use — set it in CI, where a branch may install a second provider to test against.

A cloud branch therefore needs no `CLOUD_PROVIDER` anywhere in its estate: installing its own
provider package is the whole of the configuration.

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
