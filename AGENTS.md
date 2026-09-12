# Acme

## Starting a new project

This scaffold was derived from Mention. `docs/bootstrap.md` takes an empty GCP folder to a first deploy; `docs/rename.md` lists every place the `acme` placeholder, the project ids, and the domain live. `docs/add-service.md` lists every place a new service must be registered, and `docs/remove-sample.md` retires the `notes` sample once a real service replaces it.

## Agent guidance parity

Shared guidance is canonical under `.agents/`:

- Before changing code, use `.agents/rules.json` path scopes to read the applicable files in `.agents/rules/`.
- Reusable workflows live in `.agents/skills/` and load only when relevant.
- `.claude/` and `.cursor/` contain native mirrors. Do not edit generated mirrors directly.
- After changing `AGENTS.md`, `CLAUDE.md`, or any agent rule or skill, run `m sync-agent-parity`, then `m check-agent-parity`.

## Service communication

Services talk to each other only through commands and events via the outbox. Synchronous service-to-service calls (REST, gRPC, imported clients) are strictly banned; see `.agents/rules/service-communication.md`.

## Repository commands

Use the `m` CLI for repository tasks. Do not invoke underlying scripts, `make`, `tsc`, `gcloud`, or Terraform directly.

Before checks, run `m run-code-formatting`, then the narrowest matching validator:

| Scope | Check |
| --- | --- |
| `apps/web`, `apps/mobile`, `apps/mcp` | `m run-checks-frontend` |
| `library`, `services/*` | `m run-checks-backend` |
| Cross-cutting or pre-merge | `m run-checks` |

When backend API contracts change, run `m compile-api`; never hand-edit generated clients.

Deployment changes shared infrastructure. Run deployment targets only when the user explicitly asks.
