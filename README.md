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
| `cloud/gcp` | Implemented; fresh-account onboarding unverified. Terraform for a GCP folder with operations, production, and per-branch feature projects. |
| `cloud/aws` | Implemented; fresh-account onboarding unverified. Terraform for an AWS account with a VPC, ECS Fargate services, and per-branch feature environments. |
| `cloud/azure` | Implemented; fresh-account onboarding unverified. Terraform for an Azure subscription with Container Apps and per-branch feature environments. |

## Start a product

The standalone beta creates a project and opens your installed Claude Code or Codex
to guide setup. Bring your existing agent account. Once version `0.1.0b1` is published:

```sh
uvx --from mention-template==0.1.0b1 mention-template
```

The package and snapshots are not published by committing this implementation. Follow
[Getting started](docs/getting-started.md) for prerequisites, resuming, and the checkout-based
contributor route. See [Template releases](docs/template-releases.md) for publication steps.

The CLI exports a committed cloud snapshot, previews project configuration, and checks readiness.
The first milestone is the deployed notes web sample in demo. Monitoring, admin, MCP, mobile, and
production setup follow separately. Fresh-account deployment status is recorded honestly in
[Setup verification](docs/setup-verification.md).

The multi-cloud branch rules describe maintenance of this template. A generated product uses normal
main-branch development and does not inherit the template's multi-branch workflow.

To define the product's brand and application design, ask an agent to use the `define-design`
skill. It explores your audience, products and brands you like or dislike, and representative
screens, then records your choices in `docs/product/design.md`. The sample's styling is a
replaceable starting point, not a design direction your product must follow.
