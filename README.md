# acme

A scaffold for a new product on the Mention platform architecture. It is a complete, deployable
system with the business logic reduced to one thing: a user writes a note and the system
summarizes it with an LLM.

What is here: a backend in the language you choose — a shared kernel (`library/`), one
domain-driven service (`services/notes`) with a REST server, an event listener, a command executor,
a scheduled job, and the outbox triggers, and the schema-change backfills (`backfills/`); the
language-neutral control plane (`control-plane/`) of ports, domain primitives and the local
provider that every backend builds on; an admin control plane (`admin/`) that launches backfills and
seeds environments; a web app (`apps/web`), a mobile app (`apps/mobile`), and an MCP server
(`apps/mcp`); the `m` CLI that drives all of it; and agent guidance under `.agents/`.

## Branches

`main` is the language-free, cloud-free base. The backend lives on one branch per language and the
infrastructure to deploy it on one branch per cloud; each adds files that `main` does not have, and
a product is generated from a leaf that merges one of each:

| Branch | Status |
| --- | --- |
| `lang/python` | Implemented. The Python backend: `library`, `services/notes`, `backfills`, their image recipes and the OpenAPI generator. |
| `cloud/gcp` | Implemented; fresh-account onboarding unverified. Terraform for a GCP folder with operations, production, and per-branch feature projects. |
| `cloud/aws` | Implemented; fresh-account onboarding unverified. Terraform for an AWS account with a VPC, ECS Fargate services, and per-branch feature environments. |
| `cloud/azure` | Implemented; fresh-account onboarding unverified. Terraform for an Azure subscription with Container Apps and per-branch feature environments. |
| `python/gcp`, `python/aws`, `python/azure` | The leaves products are generated from: `main` + `lang/python` + `cloud/<c>`, kept in step by `m sync-branches`. |

A TypeScript backend (`lang/ts`, leaves `ts/<cloud>`) is planned; `docs/cloud-providers.md`
describes the topology and the rule every branch obeys.

## Start a product

The standalone beta creates a project and opens your installed Claude Code or Codex
to guide setup. Install uv, Git, and your chosen agent, then run:

```sh
uvx mention-template
```

Version `0.1.0b1` is published on PyPI with public cloud snapshots. Follow
[Getting started](docs/getting-started.md) for prerequisites, resuming, and the checkout-based
contributor route. See [Template releases](docs/template-releases.md) for maintainer release steps.

The CLI exports a committed leaf snapshot, previews project configuration, and checks readiness.
The first milestone is the deployed notes web sample in demo. Monitoring, admin, MCP, mobile, and
production setup follow separately. Fresh-account deployment status is recorded honestly in
[Setup verification](docs/setup-verification.md).

The branch rules describe maintenance of this template. A generated product uses normal
main-branch development and does not inherit the template's multi-branch workflow.

To define the product's brand and application design, ask an agent to use the `define-design`
skill. It explores your audience, products and brands you like or dislike, and representative
screens, then records your choices in `docs/product/design.md`. The sample's styling is a
replaceable starting point, not a design direction your product must follow.
