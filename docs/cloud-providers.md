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

## What is not yet split

`library/library/infrastructure/` still imports Firestore, Pub/Sub, and Cloud Tasks directly —
including in `repository.py`, `unit_of_work.py`, and `outbox.py`, which are generic classes rather
than adapters, and in the trigger and listener modules under
`library/library/presentation/service/`. Those files are on `main` today in their GCP form.

This is deliberate and temporary. `cloud/gcp` is unaffected, but `cloud/aws` and `cloud/azure`
cannot work until that code sits behind ports, because as it stands they would have to edit files
`main` also owns — exactly what the one rule forbids.

The port extraction is the prerequisite for a second cloud, and `docs/ports-and-adapters.md` is the
plan for it: what is coupled, the ports that replace it, how a provider is selected, and the order
the work lands in. It adds `library/providers/<cloud>/` as a new slot — a distribution of its own
rather than a package inside `library`, so that the cloud's SDKs stay out of `library/pyproject.toml`.
Read it before starting work on a second cloud, and before writing any Terraform for one.
