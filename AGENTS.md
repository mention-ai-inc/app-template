# Acme

## Cloud providers

`main` is the cloud-agnostic base. Each cloud lives on its own branch — `cloud/gcp`, `cloud/aws`, `cloud/azure` — and adds provider files that `main` does not have. A cloud branch never edits a file `main` also has; that is what keeps `git merge main` conflict-free. `main` merges into the cloud branches and nothing merges back. Read `docs/cloud-providers.md` before touching anything under `infrastructure/terraform/`, `infrastructure/cli/provider/`, `infrastructure/docker/provider/`, or `.github/workflows/`.

Deployment targets (`m deploy-*`, `m terraform-*`, the feature-environment targets) exist only on a cloud branch. Everything else — checks, tests, `m compile-api`, `m run-web`, `m run-mobile` — works on `main`.

## Starting a new project

This scaffold was derived from Mention. `docs/bootstrap.md`, on the cloud branch, takes an empty account to a first deploy; `docs/rename.md` lists every place the `acme` placeholder, the project ids, and the domain live. `docs/add-service.md` lists every place a new service must be registered, and `docs/remove-sample.md` retires the `notes` sample once a real service replaces it.

`docs/product/` is where the product itself gets written down: `overview.md` for the thesis, `glossary.md` for the terms every PRD uses, `prds/` for the requirements, and `defects.md` for bugs. All four ship as stubs — fill them in rather than inventing a parallel structure.

## Agent guidance parity

Shared guidance is canonical under `.agents/`:

- Before changing code, use `.agents/rules.json` path scopes to read the applicable files in `.agents/rules/`.
- Reusable workflows live in `.agents/skills/` and load only when relevant.
- `.claude/` and `.cursor/` contain native mirrors. Do not edit generated mirrors directly.
- After changing `AGENTS.md`, `CLAUDE.md`, or any agent rule or skill, run `m sync-agent-parity`, then `m check-agent-parity`.

## Service communication

Services talk to each other only through commands and events via the outbox. Synchronous service-to-service calls (REST, gRPC, imported clients) are strictly banned; see `.agents/rules/service-communication.md`.

## Product documentation

`docs/product/prds/` holds the product requirements. Every PRD describes the product as it is meant to
be today: a later decision that changes a requirement is folded into the PRD that owns it, never left
as an amendment beside a stale original. Relationships between PRDs live in header fields that bind at
requirement granularity, and half of them are generated. Read `.agents/rules/prd-structure.md` before
writing or changing a PRD, then run `m sync-prd-links` and `m check-prd-links`.

A bug that needs no product decision is not a PRD. It belongs in `docs/product/defects.md`.

## Repository commands

Use the `m` CLI for repository tasks. Do not invoke underlying scripts, `make`, `tsc`, a cloud provider CLI, or Terraform directly.

Before checks, run `m run-code-formatting`, then the narrowest matching validator:

| Scope | Check |
| --- | --- |
| `apps/web`, `apps/mobile`, `apps/mcp` | `m run-checks-frontend` |
| `library`, `services/*` | `m run-checks-backend` |
| Cross-cutting or pre-merge | `m run-checks` |
| `docs/product/prds` | `m sync-prd-links`, then `m check-prd-links` |

When backend API contracts change, run `m compile-api`; never hand-edit generated clients.

Deployment changes shared infrastructure. Run deployment targets only when the user explicitly asks.
