# acme

A scaffold for a new product on the Mention platform architecture. It is a complete, deployable
system with the business logic reduced to one thing: a user writes a note and the system
summarizes it with an LLM.

What is here: a Python shared kernel (`library/`), one domain-driven service (`services/notes`)
with a REST server, an event listener, a command executor, a scheduled job, and the outbox
triggers; an admin control plane (`admin/`) with backfills and seeding; a web app (`apps/web`), a
mobile app (`apps/mobile`), and an MCP server (`apps/mcp`); the `m` CLI that drives all of it; and
agent guidance under `.agents/`.

## Branches

`main` is the cloud-agnostic base and holds everything above. The infrastructure to deploy it lives
on one branch per cloud, each of which adds provider files that `main` does not have:

| Branch | Status |
| --- | --- |
| `cloud/gcp` | Complete. Terraform for a GCP folder with operations, production, and per-branch feature projects. |
| `cloud/aws` | Complete. Terraform for an AWS account with a VPC, ECS Fargate services, and per-branch feature environments. |
| `cloud/azure` | Complete. Terraform for an Azure subscription with Container Apps and per-branch feature environments. |

Clone `main` to work on the product; clone a `cloud/*` branch to get something you can deploy.
`docs/cloud-providers.md` explains the slots, the merge discipline, and what a new cloud must
provide.

To start a product from it: create a repository from this template, check out the branch for your
cloud, work through `docs/rename.md` to replace the `acme` placeholders, then `docs/bootstrap.md`
to stand up the account and ship. Build the first real service with the `build-feature` skill and
`docs/add-service.md`, then retire the sample with `docs/remove-sample.md`. Day to day, `AGENTS.md`
is the entry point for the conventions and the commands.
