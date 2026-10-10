# Acme

## Backend languages and cloud providers

In this template (no root `project.json`), `main` is the language-free, cloud-free base. Each backend language lives on its own branch — `lang/python` today — and each cloud on its own — `cloud/gcp`, `cloud/aws`, `cloud/azure`; a leaf such as `python/gcp` merges `main` with one of each, and products are generated from leaves only. A branch only ever adds files that `main` does not have and never edits a file `main` also has; that is what keeps `git merge main` conflict-free. `main` merges outward through `m sync-branches` and nothing merges back; `m check-branches` verifies the topology. Read `docs/cloud-providers.md` before touching anything under `library/`, `services/`, `backfills/`, `infrastructure/cli/language/`, `infrastructure/terraform/`, `infrastructure/cli/provider/`, `infrastructure/docker/`, or `.github/workflows/`.

In a generated product (root `project.json` exists), `main` includes the selected language and provider. Ordinary application and infrastructure edits belong on that main branch; the template-only branch restrictions above do not apply. Read `docs/getting-started.md` and use `start-project` for initial setup.

Deployment targets (`m deploy-*`, `m terraform-*`, the feature-environment targets) exist when provider files are installed, including on a generated product’s main branch. The backend language packages (`library`, `services/*`, `backfills`) and the OpenAPI generator behind `m compile-api` exist when a `lang/*` branch's files are installed. Everything else — checks, tests, `m check-api-contract`, `m run-web`, `m run-mobile` — works on `main`.

## Starting a new project

This scaffold was derived from Mention. `docs/bootstrap.md`, on the cloud branch, takes an empty account to a first deploy; `docs/rename.md` lists every place the `acme` placeholder, the project ids, and the domain live. `docs/add-service.md` lists every place a new service must be registered, and `docs/remove-sample.md` retires the `notes` sample once a real service replaces it.

`docs/product/` is where the product itself gets written down: `overview.md` for the thesis, `glossary.md` for the terms every PRD uses, `prds/` for the requirements, and `defects.md` for bugs. All four ship as stubs — fill them in rather than inventing a parallel structure.

`docs/product/design.md` holds the fork's brand and application design decisions. The starter UI is
provisional. Use the `define-design` skill for a guided discussion of the audience, inspiration, and
design direction, then record the agreed brief there.

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
| `library`, `services/*`, `backfills` (the backend language packages) | `m run-checks-backend` |
| `control-plane`, `admin` | `m run-checks-backend` |
| Cross-cutting or pre-merge | `m run-checks` |
| `docs/product/prds` | `m sync-prd-links`, then `m check-prd-links` |

When backend API contracts change, run `m compile-api` on a branch that has the backend language installed; never hand-edit `packages/acme-api/openapi.json` or the generated clients. `m check-api-contract` fails when either is out of date; `docs/cloud-providers.md` describes how the regenerated files reach `main` in this template.

Deployment changes shared infrastructure. Run deployment targets only when the user explicitly asks.
