# admin

Operational tooling for the two recurring administrative concerns, served as an HTTP control-plane
API at `https://{env}admin.acme.example.com` and driven by a thin CLI:

- **`backfill`** — run schema-change migrations discovered under `backfill/migrations/`
  (`list`, `run <name>`). Legitimately targets production.
- **`seed`** — seed a feature environment with an organization, an admin user, and a few notes
  written through the notes REST API (`run`). Feature environments only.

`common/` holds the shared layer: feature-environment resolution and the production guard
(`environment.py`), the `--apply` option and async adapter (`options.py`), and the extended Clerk
client (`clerk.py`). `server/` is the FastAPI control plane; `client/` is the HTTP client the CLI
commands call.

## Architecture

Admin names no cloud. It reaches its control plane through three ports —
`IJobRunner`, `ILogReader` and `IOperatorAuth` in `library/library/application/ports/` — and the
installed provider decides what they mean. Each cloud branch's `PROVIDER.md` says which services
back them there.

The API runs as the `{env}admin-s-rest` component at `{env}admin.acme.example.com`, behind whatever
gate that cloud terminates logins with. The gate hands the application a header naming the caller;
`IOperatorAuth` turns it into an `Operator`, and admin then checks that email against the
`STAFF_ALLOWLIST` environment variable. Admin verifies the header itself rather than trusting the
gate's presence, so a detached gate fails closed rather than open.

Slow operations launch one of two jobs and return an execution id the caller polls via
`GET /runs/{execution_id}`:

| Job | Command | Environments |
| --- | --- | --- |
| `{env}admin-j-backfill` | `admin backfill` | feature + production |
| `{env}admin-j-seed` | `admin seed` | feature only |

The seed job is not created in production at all, so no request — however buggy — can seed
production. Job launches override container *args* only; each job's command is pinned in Terraform.

Every authenticated request publishes audit events (actor = the verified operator email) to the
`{env}admin_audit` collection, fanned out to the `{env}audit_events` topic by the
`{env}admin-t-publish-audit-event` trigger. Global operations (e.g. a backfill without
`--organization-id`) publish one event per organization sharing the execution id.

## Running

Go through the `m` CLI. The `m` wrapper needs `--` before the Typer arguments.

The CLI does not call the API. Every gate that fronts admin terminates a browser login and admits no
machine, so the CLI resolves the same ports the server uses and launches the job itself, with your
own cloud credentials — then polls the execution and prints its logs. The deployed API is for people
in a browser; the audit record a CLI launch writes names whoever ran it, from
`IOperatorAuth.caller_identity()`.

```
m admin -- backfill list
m admin -- backfill run note-word-count
m admin -- backfill run note-word-count --apply
m admin -- backfill run note-word-count --apply --organization-id org_XXXX
m admin -- seed run                                   # org from FEATURE_ENVIRONMENT_SEED_ORGANIZATION_ID, else created
m admin -- seed run --organization-id org_XXXX
```

The same commands work against production (`git checkout main`, or `FEATURE_ENVIRONMENT=`): the API
at `admin.acme.example.com` serves only `backfill`, `/organizations`, `/runs`, and `/operations`;
the seed route does not exist there. `GET /organizations` lists every Clerk organization in the
environment (id, name, slug).

Inside the job container (`COMPONENT_TYPE=job`, which every cloud's job module sets) the same
commands execute their workers directly against the stores; that is how the jobs themselves run.

`GET /operations` and `m admin -- backfill list` report the deployed image digest and commit sha —
check them before running a backfill you just wrote: a backfill only exists once its image is
deployed.

## Seeding

`seed run` provisions the seed admin (`seed.admin+clerk_test@acme.example.com`) in Clerk, resolves
the organization — `--organization-id`, else `FEATURE_ENVIRONMENT_SEED_ORGANIZATION_ID`, else one it
creates and records under `admin/data/seed/<env>.json` for the next run — makes the admin an
`org:admin` there, mints an impersonation token for the notes service, and writes three notes through
`POST /rest/notes/notes`. It is idempotent: a note whose title already exists is skipped. The job
needs `CLERK_SECRET_KEY`, and its identity must be able to sign JWTs as `{env}notes-s`.

## Deploying

`m deploy-admin` builds the admin image from your working tree and points the server, the audit
trigger, and every existing job at it (pinned by digest, with `COMMIT_SHA` and `IMAGE_DIGEST` set on
the server). Production images build in CI: dispatch the **Deployment** workflow with the `admin`
input checked. Infrastructure lives in its own Terraform stack: `m terraform-admin`.

Some clouds need the edge gate registered by hand before the first `m terraform-admin`. Each branch's
`docs/bootstrap.md` says whether and how.

## Safety

Every backfill route defaults to a **dry run** (`apply: false`) and `backfill run` takes `--apply`.
`seed run` writes by design, and refuses to run against production twice over: its route is absent
from the production API, and the job it launches does not exist in the production project.

## Adding a backfill

Drop a new `YYYYMMDD_<slug>.py` module under `backfill/migrations/` exposing a module-level
`BACKFILL = Backfill(name=..., description=..., run=_run)`. `run` takes keyword-only `environment`,
`apply`, and optional `organization_id`. Discovery is automatic and ordered by filename.
`20260911_note_word_count.py` is the reference shape: the provider's document store against a
permissive model, idempotent, dry run by default, with its test in `tests/test_note_word_count.py`.
Deploy the image (`m deploy-admin`, or the Deployment workflow for production) before running it. The
job runs the *deployed* image, so a backfill it does not contain exits non-zero rather than running
nothing; `m admin -- backfill list` reports the deployed digest so you can check first.
