---
name: deploy-branch
description: Ship the current branch end to end - commit, push, open a PR that records the production deploy plan, wait for checks, squash merge, watch the demo deploy, then run the branch's backfills and dispatch the production deployment.
---

# Deploying a branch

Drives a branch from working tree to demo, then straight on to production. The PR body
is the durable record of the production plan, so a later session can resume at "Production" with
nothing but the PR number.

Deploys run through GitHub Actions; **backfills do not** — there is no Backfill workflow, and they
run only through the `m admin` CLI (section 7). `gh` is required — no MCP tool can dispatch a
workflow. Preflight `gh auth status`; the token needs the `repo` scope, which covers both dispatching
workflows and reading runs. If it is invalid, stop and ask the user to run
`gh auth login -h github.com` (suggest they type `! gh auth login -h github.com`). Do not attempt to
work around a bad token.

Production needs no separate go-ahead: invoking this skill is the approval, and the run continues
through section 7 without stopping to ask. Stop only when something earlier failed or when the plan
itself is uncertain (an ordering the diff does not settle, a `terraform_operations` apply).

**Worktrees.** `m` refuses to run when the repository root's basename is not the repository's
name (`infrastructure/cli/_bin/m`; see `docs/rename.md`), which is every `.claude/worktrees/*` checkout, and a worktree has
no `.venv`s either. From a worktree, either run `m` targets from the main checkout, or invoke
`gmake -f infrastructure/cli/Makefile <target>` from the worktree root. Anything that builds an image
from the local tree (`m deploy-*`) uses **that checkout's** working tree, so `git pull` the main
checkout after the merge before deploying from it — otherwise you ship the pre-merge code and it
looks like it worked.

## 1. Preflight and commit

- Confirm the branch is not `main` and `git status` is understood. Show the user the diff summary
  (`git diff --stat origin/main...HEAD` plus uncommitted work) before committing anything.
- If the branch touched `library/`, run `m update-local-dependencies` — checks otherwise fail with
  spurious "partially unknown" errors.
- If it touched `AGENTS.md`, `CLAUDE.md`, `.agents/`, `.claude/`, or `.cursor/`, run
  `m sync-agent-parity` then `m check-agent-parity`.
- Run `m run-code-formatting`, then the narrowest validator from `AGENTS.md` (`m run-checks-frontend`,
  `m run-checks-backend`, or `m run-checks`). CI runs the full suite; catching it locally saves a
  round trip. If the user says skip, skip.
- Commit remaining changes in one commit with a message describing the whole branch's intent.

## 2. Build the deploy plan (before opening the PR)

Derive it from `git diff --name-only origin/main...HEAD`:

| Changed path | Consequence |
| --- | --- |
| `services/<name>/**` | that service deploys |
| `library/**` | **every** service deploys (demo does this automatically; production has no library checkbox, so tick each service by hand) |
| `apps/web/**` | `web` |
| `apps/mcp/**` | `mcp` (also gates the MCP terraform step) |
| `apps/mobile/**` | separate `mobile-deployment.yaml` dispatch — `deployment.yaml` does not cover mobile |
| `infrastructure/terraform/configurations/operations/**` | `terraform_operations` |
| `admin/admin/backfill/migrations/<new file>` | a backfill; its name is the `Backfill(name=...)` in the module |

Cross-check backfill names against `m admin -- backfill list` (see section 7 for the IAP env it
needs; the deployed admin image is what answers, so a name missing there means admin has not been
redeployed since the migration landed).

Then decide **order**, which is branch-specific and is the part worth thinking hardest about:

- A schema change whose documents are not yet migrated breaks reads the moment the new code is live,
  so its backfill normally runs **before** the services deploy. It cannot run before the *merge*,
  though: the production admin image is built from `main` only (section 7), so the sequence for a
  required-field change is merge → deploy admin → backfill → deploy the services that read the field.
- **Unless the deployed code rewrites those documents.** A save writes the whole document, so code
  that does not yet know the new field strips it straight back out, and the backfill never converges.
  Ask which collections the running services write on a schedule or in a pipeline (a summary
  sweep, a purge job) as opposed to only on a user action (a note a person edits). For the former,
  deploy first and backfill immediately after, accepting that unmigrated documents fail to load in
  between; say plainly how long that window is and get the user to agree to it.
- The reverse happens too: a backfill that emits events, or one whose job image needs new code, needs
  its service deployed **first**. When a backfill re-fires domain events, the consumers must already
  be on the new code.
- If two surfaces have a contract between them (web calling a service endpoint that gained a required
  body, for example), the tolerant side goes first.

If the ordering is not obvious from the diff, ask the user rather than guessing.

## 3. Push and open the PR

Push the branch, then open a PR whose body ends with this block, filled in. It is the resume
contract — keep the headings verbatim.

```markdown
## Production deployment

Backfills (in order, `m admin -- backfill run <name>` from a `main` checkout, run by an engineer):

1. `<backfill-name>` — <one line: what it migrates, and any `--organization-id` narrowing>

Deploy (GitHub Actions → Deployment, workflow_dispatch, ref `main`):

- [ ] notes
- [ ] web
- [ ] mcp
- [ ] admin
- [ ] terraform_operations

Order: <e.g. "backfill `foo` (apply) → deploy notes + web", or "deploy web → backfill `foo` → deploy notes">

Mobile: <"not affected" or "dispatch Mobile Deployment, profile=production, platform=ios">
```

Tick only the boxes the diff requires — they are exactly the `workflow_dispatch` inputs in
`deployment.yaml`, so check that file rather than trusting this list. Tick `admin` whenever the
branch adds a backfill: the production admin image is what carries the migration. Omit backfill
entries entirely if there are none — say "None" so a later reader knows it was considered, not
forgotten.

## 4. Wait for checks

`gh pr checks <number> --watch --fail-fast`.

Five checks report: `run-checks`, `vulnerability-scan`, `run-backend-tests`, `validate-schemas`, and
`update-feature-environment` — the last reports as `skipping` unless the PR carries the
`needs-feature-environment` label, which is a pass. The org-level workflows (Dependency Graph,
Security Risk Assessment, Dependabot) do not report as PR checks. A `deploy` check appears only
after merge; that is the demo deploy from section 6, not something to wait on here.

**`validate-schemas` validates *production* data against this branch's schemas.** A branch that adds
a required field will fail it until the production backfill has run — that is the check working, not
a flake. Read the PR comment it posts: it names each offending document and field, which is how you
tell this from an ordinary failure.

**This one is expected to stay red through the merge, and that is correct.** The backfill needs the
migration in the production admin image, which builds from `main` only, so it cannot run before the
merge. `main` carries no branch protection, so `gh pr merge --squash` goes through with that single
check red. Say so explicitly to the user, get their go-ahead, and record the reasoning in the PR
body. Every other check must be green first.

For other failures: report the failing job with its log excerpt, fix if the fix is clearly in scope,
push, and re-watch. Do not merge red for any other reason.

Two failures worth recognising because they are cheap to fix and easy to misread:

- `run-checks` failing on `packages/acme-api/src/api.d.ts` being out of date means `m compile-api`
  was not run. Regenerating may also produce unrelated churn (a pydantic/FastAPI upgrade can collapse
  a `Foo-Input`/`Foo-Output` schema split into one `Foo`); check whether `origin/main` regenerates the
  same way before assuming your branch caused it, and fix the call sites rather than hand-editing the
  generated file.
- Prettier runs over `apps/web`, `apps/mcp` and `apps/mobile` only. Use the pinned version
  (`prettier` in the root `package.json`) — a newer one reformats untouched files.

## 5. Squash merge

`gh pr merge <number> --squash`.

Squash is the only method the repo allows, and for a reason worth knowing: the demo deploy detects
changed services with `get_changed.py --compare-to=previous`, i.e. `HEAD~1`. A merge commit would
make that diff wrong and services would silently not deploy. The branch is deleted automatically.

Write the squash commit message to describe the branch, not to concatenate the commits.

## 6. Watch the demo deploy

Merging fires `deployment.yaml` on `pull_request: closed`. That run's `displayTitle` is the PR
title and its event is `pull_request`, which distinguishes it from the production dispatches in the
same list:

```bash
gh run list --workflow=deployment.yaml --event=pull_request --limit 3 \
  --json databaseId,displayTitle,status,createdAt
gh run watch <id>
```

The demo leg applies services and MCP terraform, deploys changed services (all of them if `library/`
changed), and deploys web. Report what actually deployed from the run log rather than from the plan.

If the branch has backfills, they have **not** run on demo, and until they do a schema change leaves
demo broken — new code reading unmigrated documents. Ask whether to run them there. From a **current
`main` checkout** (the image is built from the local tree, so pull first):

```bash
FEATURE_ENVIRONMENT=demo m deploy-admin
FEATURE_ENVIRONMENT=demo m admin -- backfill run <name> --apply
```

`m admin` calls the IAP-gated admin API, impersonating `terraform@` and minting an ID token against
that environment's IAP OAuth client (read from the project's `ADMIN_IAP_OAUTH_CLIENT_ID` secret).
That works for demo and every feature environment, because `iap.tf` grants the service account
access everywhere except production. Dry-run first (drop `--apply`) and read the job logs it
prints — for an LLM-backed backfill that output is your only review of what it will write.

Confirm demo is up: `https://demoapi.<domain>/rest/<service>/openapi` should serve the spec, and
new routes should appear in it. Browser-level verification needs a signed-in human (see the `verify`
skill).

## 7. Production

Continue here directly once demo is verified; do not ask first. Before dispatching, check the clock
against anything the plan calls out (a cron slot the old code still fires on, such as the
nightly `purge_notes` job) and wait out the window rather than asking about it.

Read the plan back from the PR body (`gh pr view <number> --json body`) rather than from memory —
this step frequently runs in a fresh session.

**Always dispatch from `main`.** `.envrc` derives `FEATURE_ENVIRONMENT` from the current branch and
blanks it only on `main`, so a `workflow_dispatch` on any other ref silently becomes a *feature*
deploy: the image builds into the feature project and fails with
`gcloud.builds.submit NOT_FOUND: Unknown service account`, while the terraform steps still apply
against production. Pass `--ref main` explicitly.

**Backfills.** `m admin -- backfill run` does **not** work against production, and no amount of
credential juggling makes it. `iap.tf` builds `iap_accessors` as engineers plus the terraform service
account *only when not production* (`local.is_production ? [] : [...]`), so impersonation returns
`403`; and a personal ADC mints its ID token against Google's shared gcloud OAuth client, whose
`aud` is not in `programmatic_clients`, so it returns a `401` saying the token's `aud` does not match.
`mint_identity_token` (`admin/admin/client/api.py`) refuses an empty `FEATURE_ENVIRONMENT` up front
for this reason. Do not try these in turn; go straight to the job.

**Execute the Cloud Run job directly.** That is exactly what the admin API does once it has
authenticated, minus the audit event, and it runs as the engineer's own gcloud identity:

```bash
gcloud run jobs execute admin-j-backfill --project <production-project> --region us-central1 \
  --args="run,<backfill-name>" --wait
gcloud run jobs execute admin-j-backfill --project <production-project> --region us-central1 \
  --args="run,<backfill-name>,--apply" --wait
```

The job takes the bare `backfill` CLI arguments — `run <name> [--apply] [--organization-id <id>]`. There is no `--confirm production`; that flag is a client-side guard in
`m admin` and the job rejects it. `--wait` returns when the execution finishes but prints nothing the
backfill wrote, so read the output from Cloud Logging using the execution name it echoes:

```bash
gcloud logging read 'resource.type="cloud_run_job" AND
  labels."run.googleapis.com/execution_name"="<execution>"' \
  --project <production-project> --limit 50 --format='value(textPayload)'
```

The job runs the **deployed** admin image, so admin must have deployed first — see the two-dispatch
ordering below. Dry run first, read its logging output, then apply — unless the user waives the dry
run. Add `--organization-id` when the plan narrows the run. Finish one backfill
before starting the next; do not fan them out.

Demo and feature environments are different: there `m admin -- backfill run` works, because the
terraform service account *is* an `iap_accessors` member. Use the impersonation form from section 6,
and note the job name carries the environment prefix there (`demoadmin-j-backfill`, in the
feature project).

**Deployment.** One dispatch with the ticked boxes:

```bash
gh workflow run deployment.yaml --ref main -f notes=true -f web=true
```

**A branch with a backfill needs two dispatches, not one.** Within a single dispatch
`deployment.yaml` runs its steps in file order: services terraform → services → web → admin
terraform → mcp → **admin last**. Ticking `admin` alongside the services therefore deploys the
migration *after* the code that depends on it, which is backwards. Split it:

1. `gh workflow run deployment.yaml --ref main -f admin=true` — the admin image carrying the
   migration. This also applies services terraform, which is usually what you want first anyway.
2. Run the backfill (see above).
3. `gh workflow run deployment.yaml --ref main -f <services> -f web=true`.

Keep the gap between 2 and 3 short, and say plainly in the plan what can happen inside it: the old
code is still live and can write documents back in the old shape, undoing part of the backfill. Note
too that step 1's terraform apply already destroys any executor or job the branch removed, so
commands the old code still dispatches to it are dropped from that moment, not from step 3.

Notes that bite:
- Services terraform applies on **every** production dispatch, regardless of inputs. So a dispatch
  you think is a no-op can still apply drift that has accumulated in `main`'s terraform; read the
  plan in the log before assuming nothing changed.
- MCP terraform applies only when `mcp=true`; admin terraform and the admin image deploy only when
  `admin=true`.
- `terraform_operations=true` applies operations terraform — shared infrastructure. Confirm with the
  user before including it even if the diff implies it.
- There is no library checkbox. Library changes mean ticking every service explicitly.

Watch the run. If it fails partway, report exactly which steps succeeded before re-dispatching —
re-running a full dispatch re-applies terraform.

**Mobile**, if the plan calls for it:

```bash
gh workflow run mobile-deployment.yaml --ref main -f profile=production -f platform=ios -f submit=true
```

**Only this combination ships.** `profile=preview` is `distribution: internal` (ad hoc) in
`apps/mobile/eas.json`, which cannot go to TestFlight at all — the submit fails on an input prompt
with no stdin. And `platform=all` fails at Submit on any profile: the Android leg wants
`./credentials/google-play-service-account.json`, which is gitignored and absent in CI, and it runs
*first*, so iOS never submits even though both builds succeeded. Do not "fix" a failed submit by
re-dispatching the same inputs.

If a build already succeeded and only the submit failed, recover without paying for a rebuild by
submitting the existing artifact from `apps/mobile`:

```bash
pnpm exec eas submit --non-interactive --latest --profile production --platform ios
```

The App Store Connect API key lives on EAS servers, so this needs no local Apple credentials — but
`--latest` picks the newest build **for that profile**, so the profile must match the build you want.

## 8. Report

Close with: PR number and merge commit, what deployed to demo, what ran and deployed in production
(backfills with apply status, services, terraform), and anything left undone. If production did not
ship, say plainly why, that the branch is live on demo only, and point at the PR body.
