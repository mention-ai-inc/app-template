# Azure

This branch is Azure's provider branch: `main`, plus the provider slots `docs/cloud-providers.md`
defines and nothing else. Read that document first. It defines the one rule that keeps this branch
mergeable: everything added here is a file `main` does not have. If something on `main` needs to
behave differently on Azure, add a hook to the slot on `main` and put the behaviour in the slot —
never edit the shared file here.

## Slots

- [x] `infrastructure/terraform/` — modules, plus configurations named `operations`, `services`,
      `web`, `mcp`, and `admin`.
- [x] `library/providers/azure/` — the Azure data plane behind the ports in `library/library/application/ports/`.
- [x] `infrastructure/cli/provider/targets.mk` — every `m` target listed under "Required `m` targets"
      in `docs/cloud-providers.md`.
- [x] `infrastructure/cli/provider/deployment/` — the scripts those targets run.
- [x] `infrastructure/cli/provider/helpers/` — helpers used only by those scripts.
- [x] `infrastructure/cli/provider/envrc` — subscription, tenant, region, the `containerapp`
      extension, and `PROVIDER_REQUIRED_PACKAGES`.
- [x] `infrastructure/cli/provider/feature-environment` — `$FEATURE_ENVIRONMENT` to a resource group.
- [x] `infrastructure/docker/provider/{services,mcp,admin}/` — build and push recipes. The
      `Dockerfile`s are portable and stay on `main`.
- [x] `.github/workflows/` — `deployment.yaml`, `create-feature-environment.yaml`,
      `destroy-feature-environment.yaml`, `pull-request-cloud-checks.yaml`.
- [x] `.agents/rules.provider.json` and `.agents/rules/deployment-plan.md`.
- [x] `.agents/skills/deploy-branch/` and `.agents/skills/investigate-systems/`.
- [x] `docs/bootstrap.md` — an empty Azure subscription to a first deploy.
- [ ] A root ignore file. Azure needs none: images build locally with `docker buildx` against the
      `.dockerignore` that `main` already owns, and nothing uploads a source context to the cloud.

## What is shaped differently here

- **Feature environments are prefixes in one subscription**, as on AWS. There is one subscription and
  one tenant; operations, production and feature are resource groups, and every feature environment is
  a Terraform workspace whose name prefixes the resources it creates.
- **Pools pull.** Service Bus has no push delivery, so a pool receives from its queue or subscription
  and replays the request into its own FastAPI app in process. `SERVICE_BUS_QUEUES_JSON`,
  `SERVICE_BUS_SUBSCRIPTIONS_JSON` and `CHANGE_FEED_TRIGGERS_JSON` are how it finds its sources.
- **CI holds no secret.** Every workflow exchanges a GitHub OIDC token for an Entra token through
  `azure/login@v2` against the federated credentials in `modules/github-federation`.
- **Names are short.** Container Apps caps a name at 32 characters, so `modules/container-app-name`
  truncates and appends a digest. `infrastructure/cli/provider/helpers/container-app-name` mirrors
  that function for the scripts that have to name an app the `deployable_components` output does not
  cover.
- **The control plane needs its own role.** `IJobRunner` starts a `manual_trigger_config` job through
  the ARM jobs API, which `Reader` does not permit, so `admin-identity` carries a custom role with
  exactly `Microsoft.App/jobs/read`, `start/action` and `executions/read`. `ILogReader` queries
  `ContainerAppConsoleLogs_CL` — note that wants the workspace GUID, not the ARM resource id — and
  ingestion lags, so an execution can finish before its logs arrive.
- **The gate is the platform's.** `IOperatorAuth` reads the `X-MS-CLIENT-PRINCIPAL` header the
  container app's built-in auth injects after terminating Entra sign-in. `admin_ip_allowlist` narrows
  who can reach the login page; it is not the thing keeping anyone out.
