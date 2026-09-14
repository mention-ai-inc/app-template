## Finish every implementation with a deployment plan

Code that is written but never shipped changes nothing. When you finish implementing a task, end your
final message with a short **Deployment plan** section: the ordered `m` commands that would ship what
you just changed, derived from the actual diff. Not a generic checklist — if the diff touched two
services and a Terraform file, name those three targets and the order they run in.

Write the plan; do not run it. Deployment changes shared infrastructure, so these targets run only
when the user explicitly asks (see `AGENTS.md`). Local `m deploy-*` works against a feature
environment only — it refuses to run against production. Production ships through the **Deployment**
GitHub Actions workflow, which the `deploy-branch` skill drives end to end.

### Deriving it from the diff

| Changed path | Target |
| --- | --- |
| `services/<name>/**` | `m deploy-<name>` — `m deploy-notes` for the scaffold's one service |
| `library/**` | `m deploy-<name>` for **every** service; they all vendor the library |
| `apps/web/**` | `m deploy-web` (this also applies the web Terraform) |
| `apps/mcp/**` | `m deploy-mcp` |
| `apps/mobile/**` | no `m deploy-*` target; mobile ships via `mobile-deployment.yaml` |
| `admin/**` | `m deploy-admin` |
| `infrastructure/terraform/configurations/services/**` | `m terraform-services` |
| `infrastructure/terraform/configurations/operations/**` | `m terraform-operations` |
| `infrastructure/terraform/configurations/mcp/**` | `m terraform-mcp` |
| `infrastructure/terraform/configurations/admin/**` | `m terraform-admin` |
| a new `admin/admin/backfill/migrations/*.py` | `m admin -- backfill run <name> --apply` |

`m deploy-<service>` redeploys every component of that service, which is almost always what you want.
A service's components are its REST server, its pools, and its jobs — `m deploy-notes-pool-standard`
names one, and only when you are certain nothing else in the service changed. `m deploy-changes`
infers targets from the diff — convenient, but it hides the ordering below, so prefer explicit targets
in a written plan.

Executors, listeners, and triggers are **routes inside a pool**, not deployable units of their own.
Adding one to an existing pool ships with `m deploy-<service>` alone. What still needs
`m terraform-services` is infrastructure the route depends on: a **new pool**, a **new Cloud Tasks
queue** (that is, a new executor entry in `terraform.tfvars`), a **new Pub/Sub subscription**, a **new
Eventarc trigger**, or a **new job**.

### Ordering is the part worth thinking about

State the order explicitly and give the reason for each constraint, so a reader can check it. The
recurring ones:

- A **backfill for a newly required field** runs *before* the services that read it deploy — new code
  rejects unmigrated documents. See `no-schema-defaults`.
- A backfill that **emits domain events** runs *after* its consumers deploy, or the events land on
  code that cannot handle them.
- Where two surfaces share a contract, the **tolerant side goes first** — a client that accepts both
  shapes before the server that requires the new one.
- An **event or command payload gaining a required field** means publisher and consumer deploy
  **together**; they cannot be sequenced apart.
- Terraform that creates a subscription applies **after** the code that handles the event exists —
  the subscription pushes to a route, so the pool must already serve it or the messages dead-letter.
- A **new pool** applies before the deploy that fills it, and an executor **moving between pools** is
  a Terraform-only change: apply it, and in-flight tasks aimed at the old pool drain against the route
  it still serves.

Call out anything the plan depends on that you could not verify, and say what still needs a run in a
feature environment. If the ordering does not follow from the diff, say so and ask rather than
guessing.
