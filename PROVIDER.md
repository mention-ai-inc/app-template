# Azure

This branch is Azure's provider branch. **It is not implemented yet** — it is currently identical to
`main`, which means the repository builds, checks, and tests, but cannot deploy.

Read `docs/cloud-providers.md` first. It defines the slots and the one rule that keeps this branch
mergeable: everything added here must be a file `main` does not have. If something on `main` needs
to behave differently on Azure, add a hook to the slot on `main` and put the behaviour in the slot —
never edit the shared file here.

## Slots to fill

- [ ] `infrastructure/terraform/` — modules, plus configurations named `operations`, `services`,
      `web`, `mcp`, and `admin`.
- [ ] `infrastructure/cli/provider/targets.mk` — every `m` target listed under "Required `m` targets"
      in `docs/cloud-providers.md`.
- [ ] `infrastructure/cli/provider/deployment/` — the scripts those targets run.
- [ ] `infrastructure/cli/provider/helpers/` — helpers used only by those scripts.
- [ ] `infrastructure/cli/provider/envrc` — credentials, SDK on `PATH`, `PROVIDER_REQUIRED_PACKAGES`.
- [ ] `infrastructure/cli/provider/feature-environment` — `$FEATURE_ENVIRONMENT` to an Azure account.
- [ ] `infrastructure/docker/provider/{services,mcp,admin}/` — build and push recipes. The
      `Dockerfile`s are portable and stay on `main`.
- [ ] `.github/workflows/` — `deployment.yaml`, `create-feature-environment.yaml`,
      `destroy-feature-environment.yaml`, `pull-request-cloud-checks.yaml`.
- [ ] `.agents/rules.provider.json` and `.agents/rules/deployment-plan.md`.
- [ ] `.agents/skills/deploy-branch/` and `.agents/skills/investigate-systems/`.
- [ ] `docs/bootstrap.md` — an empty Azure account to a first deploy.
- [ ] A root ignore file, if Azure's tooling needs one.

## Blocked on the port extraction

Do not start here. `library/library/infrastructure/` still talks to Firestore, Pub/Sub, and Cloud
Tasks directly, including from generic code in `repository.py`, `unit_of_work.py`, and `outbox.py`
and from the trigger modules under `library/library/presentation/service/`. Those files are on
`main`, so filling the slots above would still leave this branch unable to run without editing them
— which the one rule forbids and which would make every future merge conflict.

Putting that code behind ports on `main`, with the adapters moving to a new
`library/library/infrastructure/providers/<cloud>/` slot, is the prerequisite. See the "What is not
yet split" section of `docs/cloud-providers.md`.
