# AWS

This branch is AWS's provider branch: `main`, plus the provider slots `docs/cloud-providers.md`
defines and nothing else. Read that document first. It defines the one rule that keeps this branch
mergeable: everything added here is a file `main` does not have. If something on `main` needs to
behave differently on AWS, add a hook to the slot on `main` and put the behaviour in the slot —
never edit the shared file here.

## Slots

- [x] `infrastructure/terraform/` — modules, plus configurations named `operations`, `services`,
      `web`, `mcp`, and `admin`.
- [x] `library/providers/aws/` — the AWS data plane behind the ports in `library/library/application/ports/`.
- [x] `infrastructure/cli/provider/targets.mk` — every `m` target listed under "Required `m` targets"
      in `docs/cloud-providers.md`.
- [x] `infrastructure/cli/provider/deployment/` — the scripts those targets run.
- [x] `infrastructure/cli/provider/helpers/` — helpers used only by those scripts.
- [x] `infrastructure/cli/provider/envrc` — region, profile or assumed role, and
      `PROVIDER_REQUIRED_PACKAGES`.
- [x] `infrastructure/cli/provider/feature-environment` — `$FEATURE_ENVIRONMENT` to a Terraform
      workspace.
- [x] `infrastructure/docker/provider/{services,mcp,admin}/` — build and push recipes. The
      `Dockerfile`s are portable and stay on `main`.
- [x] `.github/workflows/` — `deployment.yaml`, `create-feature-environment.yaml`,
      `destroy-feature-environment.yaml`, `pull-request-cloud-checks.yaml`.
- [x] `.agents/rules.provider.json` and `.agents/rules/deployment-plan.md`.
- [x] `.agents/skills/deploy-branch/` and `.agents/skills/investigate-systems/`.
- [x] `docs/bootstrap.md` — an empty AWS account to a first deploy.
- [ ] A root ignore file. AWS needs none: images build locally with `docker buildx` against the
      `.dockerignore` that `main` already owns, and nothing uploads a source context to the cloud.

## What is shaped differently here

- **Feature environments are prefixes in one account.** Operations, production and feature share a
  single account; every feature environment is a Terraform workspace whose name prefixes the
  resources it creates, and `""` is production.
- **Pools pull.** SQS has no push delivery, so a pool long-polls its queue and replays the message
  into its own FastAPI app in process. `SQS_EXECUTOR_QUEUES_JSON`, `SQS_LISTENER_QUEUES_JSON` and
  `SQS_TRIGGER_QUEUES_JSON` are how it finds its sources.
- **The change feed takes a hop.** DynamoDB Streams cannot deliver to a queue on their own, so
  `modules/dynamodb-stream-trigger` runs the stream through an EventBridge Pipe into SQS, and the
  pool reads it like any other source.
- **One table, one index.** Every collection shares a single DynamoDB table partitioned by the port's
  partition key, and queries that the key cannot answer go through `gsi1`. `DYNAMODB_COLLECTION_INDEX`
  names it so the adapter never hardcodes the Terraform's choice.
- **The load balancer owns its target groups.** `modules/application-load-balancer` creates them and
  `modules/ecs-server` is handed an ARN. The other way round deadlocks: ECS refuses a service whose
  target group has no load balancer, and a listener rule derived from the failed module can never
  recover on a retry.
- **Tasks run on Graviton.** Task definitions are ARM64, so every build recipe defaults
  `DOCKER_PLATFORM` to `linux/arm64`. An amd64 image reaches ECR and then fails at pull time.
- **CI holds no secret.** Every workflow exchanges a GitHub OIDC token for the role in
  `modules/github-oidc-role`. That role is also assumable by the engineers group, so the same
  Terraform runs from a laptop.
- **Engineer permissions are one policy.** IAM caps a group at ten managed policies, so
  `modules/permissions` builds a single customer-managed policy from a list of service actions
  rather than attaching AWS's.
