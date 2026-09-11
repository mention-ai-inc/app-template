# admin

Operational tooling for the two recurring administrative concerns, served as an HTTP control-plane
API at `https://{env}admin.acme.mentionai.app` and driven by a thin CLI:

- **`backfill`** — run schema-change migrations discovered under `backfill/migrations/`
  (`list`, `run <name>`). Legitimately targets production.
- **`seed`** — seed a feature environment with an organization, an admin user, and a few notes
  written through the notes REST API (`run`). Feature environments only.

`common/` holds the shared layer: feature-environment resolution and the production guard
(`environment.py`), the `--apply` option and async adapter (`options.py`), and the extended Clerk
client (`clerk.py`). `server/` is the FastAPI control plane; `client/` is the HTTP client the CLI
commands call.

## Architecture

The admin API runs as the `{env}admin-s-rest` Cloud Run service behind its own load balancer at
`{env}admin.acme.mentionai.app`, gated by Google Cloud IAP. Only allowlisted Google identities get
through IAP, and the service independently verifies the `x-goog-iap-jwt-assertion` header and checks
the verified email against the `STAFF_ALLOWLIST` environment variable — if IAP is ever detached, the
service fails closed. The Cloud Run service uses internal-load-balancer ingress, so its `*.run.app`
URL is unreachable.

Slow operations launch one of two Cloud Run jobs and return an execution id the caller polls via
`GET /runs/{execution_id}`:

| Job | Command | Environments |
| --- | --- | --- |
| `{env}admin-j-backfill` | `admin backfill` | feature + production |
| `{env}admin-j-seed` | `admin seed` | feature only |

The seed job does not exist in the production project (`count = local.is_production ? 0 : 1` in
`infrastructure/terraform/configurations/admin/admin.tf`), so no request — however buggy — can seed
production. Job launches override container *args* only; each job's command is pinned in Terraform.

Every authenticated request publishes audit events (actor = the IAP-verified email) to the
`{env}admin_audit` Firestore collection, fanned out to the `{env}audit_events` topic and BigQuery by
the `{env}admin-t-publish-audit-event` trigger. Global operations (e.g. a backfill without
`--organization-id`) publish one event per organization sharing the execution id.

## Running

Go through the `m` CLI. The `m` wrapper needs `--` before the Typer arguments. Commands authenticate
by impersonating the terraform service account with an ID token whose audience is the project's
`ADMIN_IAP_OAUTH_CLIENT_ID` (IAP rejects Google's shared ADC/gcloud clients, and production IAP
admits no service accounts, so production backfills execute the Cloud Run job directly). For
job-backed commands the CLI polls the execution and prints its logs:

```
m admin -- backfill list
m admin -- backfill run note-word-count
m admin -- backfill run note-word-count --apply
m admin -- backfill run note-word-count --apply --organization-id org_XXXX
m admin -- seed run                                   # org from FEATURE_ENVIRONMENT_SEED_ORGANIZATION_ID, else created
m admin -- seed run --organization-id org_XXXX
```

The same commands work against production (`git checkout main`, or `FEATURE_ENVIRONMENT=`): the API
at `admin.acme.mentionai.app` serves only `backfill`, `/organizations`, `/runs`, and `/operations`;
the seed route does not exist there. `GET /organizations` lists every Clerk organization in the
environment (id, name, slug).

Inside a Cloud Run job (`CLOUD_RUN_JOB` is set) the same commands execute their workers directly
against the stores; that is how the jobs themselves run.

`GET /operations` and `m admin -- backfill list` report the deployed image digest and commit sha —
check them before running a backfill you just wrote: a backfill only exists once its image is
deployed.

## Seeding

`seed run` provisions the seed admin (`seed.admin+clerk_test@acme.mentionai.app`) in Clerk, resolves
the organization — `--organization-id`, else `FEATURE_ENVIRONMENT_SEED_ORGANIZATION_ID`, else one it
creates and records under `admin/data/seed/<env>.json` for the next run — makes the admin an
`org:admin` there, mints an impersonation token for the notes service, and writes three notes through
`POST /rest/notes/notes`. It is idempotent: a note whose title already exists is skipped. The job
needs `CLERK_SECRET_KEY` and `GOOGLE_CLOUD_PROJECT`, and its service account must be able to sign
JWTs as `{env}notes-s`.

## Deploying

`m deploy-admin` builds the admin image from your working tree and points the server, the audit
trigger, and every existing job at it (pinned by digest, with `COMMIT_SHA` and `IMAGE_DIGEST` set on
the server). Production images build in CI: dispatch the **Deployment** workflow with the `admin`
input checked. Infrastructure lives in its own Terraform stack: `m terraform-admin`.

IAP uses a manually created Web OAuth client per GCP project (External consent screen). Before the
first `m terraform-admin` in a project, create that client with redirect URI
`https://iap.googleapis.com/v1/oauth/clientIds/<CLIENT_ID>:handleRedirect`, then store
`ADMIN_IAP_OAUTH_CLIENT_ID` and `ADMIN_IAP_OAUTH_CLIENT_SECRET` in the project's Secret Manager.

## Safety

Every backfill route defaults to a **dry run** (`apply: false`) and `backfill run` takes `--apply`.
`seed run` writes by design, and refuses to run against production twice over: its route is absent
from the production API, and the job it launches does not exist in the production project.

## Adding a backfill

Drop a new `YYYYMMDD_<slug>.py` module under `backfill/migrations/` exposing a module-level
`BACKFILL = Backfill(name=..., description=..., run=_run)`. `run` takes keyword-only `environment`,
`apply`, and optional `organization_id`. Discovery is automatic and ordered by filename.
`20260911_note_word_count.py` is the reference shape: raw Firestore, idempotent, dry run by default,
with its test in `tests/test_note_word_count.py`. Deploy the image (`m deploy-admin`, or the
Deployment workflow for production) before running it — `POST /backfills/{name}/runs` 404s for a
backfill the deployed image does not contain.
