# GCP

This branch is GCP's provider branch: `main`, plus the provider slots `docs/cloud-providers.md`
defines and nothing else. Read that document first. It defines the one rule that keeps this branch
mergeable: everything added here is a file `main` does not have. If something on `main` needs to
behave differently on GCP, add a hook to the slot on `main` and put the behaviour in the slot —
never edit the shared file here.

## Slots

- [x] `infrastructure/terraform/` — modules, plus configurations named `operations`, `services`,
      `web`, `mcp`, and `admin`.
- [x] `library/providers/gcp/` — the GCP data plane behind the ports in `library/library/application/ports/`.
- [x] `infrastructure/cli/provider/targets.mk` — every `m` target listed under "Required `m` targets"
      in `docs/cloud-providers.md`.
- [x] `infrastructure/cli/provider/deployment/` — the scripts those targets run.
- [x] `infrastructure/cli/provider/helpers/` — helpers used only by those scripts.
- [x] `infrastructure/cli/provider/envrc` — application default credentials, project, and
      `PROVIDER_REQUIRED_PACKAGES`.
- [x] `infrastructure/cli/provider/feature-environment` — `$FEATURE_ENVIRONMENT` to a project.
- [x] `infrastructure/docker/provider/{services,mcp,admin}/` — Cloud Build recipes. The
      `Dockerfile`s are portable and stay on `main`.
- [x] `.github/workflows/` — `deployment.yaml`, `create-feature-environment.yaml`,
      `destroy-feature-environment.yaml`, `pull-request-cloud-checks.yaml`.
- [x] `.agents/rules.provider.json` and `.agents/rules/deployment-plan.md`.
- [x] `.agents/skills/deploy-branch/` and `.agents/skills/investigate-systems/`.
- [x] `docs/bootstrap.md` — an empty GCP organization folder to a first deploy.
- [x] `.gcloudignore` — what `gcloud` must not upload as a build context.

## What is shaped differently here

- **Three projects, one of them shared.** Operations hosts the Shared VPC, the state bucket and the
  registry; production and feature are service projects attached to it. Feature environments are
  Terraform workspaces prefixing resources inside the feature project, so a branch costs a prefix
  rather than a project.
- **Pools are pushed to.** Pub/Sub and Cloud Tasks both deliver over HTTP into Cloud Run, so a pool
  is an ordinary server and `pool_driver()` returns `None` — the same shape `main` runs locally. AWS
  and Azure have no push delivery and have to pull.
- **The change feed is managed.** `modules/eventarc-trigger` points Eventarc at a Firestore
  collection and at the trigger pool's route. No stream, no pipe, no leases container.
- **Images build in the cloud.** Each component has a `cloudbuild.yaml` rather than a local
  `docker buildx` invocation, which is why `.gcloudignore` exists and why the build service account
  needs `logging.logWriter` and `artifactregistry.writer` before the first deploy.
- **CI holds no secret.** Every workflow exchanges a GitHub OIDC token through the workload identity
  pool in `modules/workload-identity`.
- **The control plane is pushed to as well.** `IJobRunner` is Cloud Run jobs and `ILogReader` is
  Cloud Logging, but `IOperatorAuth` is the interesting one: IAP verifies the operator before the
  request arrives and signs an assertion whose audience is the load balancer's numeric backend
  service id, so the adapter has to resolve that id at startup and keep a project-number table.
  `library_provider_gcp/cloud/` holds the REST clients all three are built on.
