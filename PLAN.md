# app-template construction plan

A scaffold cut from `~/code/mention`. Every new product starts from this repo and inherits Mention's
GCP footprint, event-driven DDD service architecture, shared kernel, admin control plane, agent
guidance, and the three app surfaces. The scaffold runs as a real app named **acme** that does one
thing: a user writes a note, the system summarizes it with an LLM.

## Decisions

| Question | Decision |
| --- | --- |
| Example domain | Notes with LLM summary: REST create, `NoteCreated` event, listener dispatches `SummarizeNote`, executor calls the LLM, scheduled purge job |
| Persistence | Firestore + Redis. Neo4j and Weaviate removed everywhere |
| Naming | Working placeholder `acme`, rename checklist in `docs/rename.md` |
| Repo | `mention-ai-inc/app-template`, marked as a GitHub template repository |
| Deploy proof | Stand up folder + projects under the Mention GCP org, deploy every surface once, destroy |
| Proof domain | Delegated zone `acme.mentionai.app`, one NS record added to Mention's `dns.tf` |
| Proof Vercel | Mention's team, project named `acme-web` |
| Proof Clerk | Fresh dev instance created during the proof |
| Auth model | Clerk organizations, every aggregate scoped by `organization_id`, as in Mention |
| Excluded | landing, extension, public docs site, models, scripts harness, widgets, BigQuery event views, copy and credits admin commands |

## Target layout

```
app-template/
  .agents/               rules + skills (canonical), mirrored to .claude and .cursor
  .github/workflows/     pull-request-checks, deployment, create/destroy-feature-environment, mobile-deployment
  admin/                 control plane: server, client, common, backfill (one example migration), seed (one phase)
  apps/web               Vite + TanStack Router + Clerk: sign in, pick org, list notes, create note, see summary
  apps/mobile            Expo Router + Clerk: same two screens
  apps/mcp               Express + MCP SDK + Clerk: list_notes, create_note
  docs/bootstrap.md      folder -> operations project -> terraform -> first deploy
  docs/rename.md         every place the name acme, the project ids, and the domain live
  infrastructure/cli     m bin + Makefile + scripts
  infrastructure/docker  services, admin, mcp images
  infrastructure/terraform/{modules,configurations/{operations,services,admin,mcp,web}}
  library/               shared kernel
  packages/acme-api      generated OpenAPI types
  packages/acme-api-client  openapi-fetch client + react-query hooks
  services/notes         the example bounded context
```

## Phase 0: repository

1. `git init` in `~/code/app-template` (done), copy root files: `.gitignore`, `.dockerignore`,
   `.gcloudignore`, `.envrc`, `.npmrc`, `.node-version`, `.python-version`, `eslint.config.mjs`,
   `tsconfig.json`, `package.json`, `pnpm-workspace.yaml`, `pyproject.toml`, `osv-scanner.toml`.
2. `.env.example` listing every key the scaffold reads, no values.
3. `pyproject.toml`: `known-first-party` becomes `admin, library, notes_service`; pyright execution
   environments reduced to library, admin, services/notes, cli helpers.
4. `package.json`: drop `@google/gemini-cli`, `marked`, and the Next eslint plugin.
5. `.envrc`: `GOOGLE_CLOUD_PROJECT` placeholder, feature-environment derivation unchanged.

Gate: `direnv allow` succeeds, `pnpm install` succeeds with an empty workspace.

## Phase 1: infrastructure and CLI

Copy `infrastructure/` whole, then prune.

**Terraform modules**: keep all except `compute-engine-neo4j`, `compute-engine-weaviate`.

**operations**: keep `projects`, `networking`, `iam`, `artifacts`, `storage`, `firewall` (drop the
neo4j and weaviate rules), `persistence` (feature Firestore database + redis password only), `dns`
(zone plus a single placeholder A record, drop Clerk, Posthog, MX, and verification records; the
proof adds Clerk records back in a branch). Drop `landing.tf`, `docs.tf`. `terraform.tfvars` gets
placeholder org, folder, billing, project ids; `gcp_services` loses calendar, docs, drive, meet,
people, picker, batch, bigquerydatatransfer, sqladmin.

**services**: keep `base`, `api`, `artifacts`, `events`, `iam`, `persistence` (Firestore + redis
only), `services`, `storage` (cache bucket, pubsub export dataset, audit export dataset and
archive), `secrets`, `outputs`. `monitoring.tf` keeps the API log sink and the redis alerts, drops
Weaviate and DAU. Drop `domain_event_views.tf`. `services.tf` env map trimmed to what the library
reads: `GOOGLE_CLOUD_PROJECT`, `FEATURE_ENVIRONMENT`, `PYTHONWARNINGS`, `REDIS_HOST`,
`REDIS_PASSWORD`, `CLERK_SECRET_KEY`, `CLERK_WEBHOOK_SECRET`, `GEMINI_API_KEY`, `SENTRY_DSN`,
`LOGFIRE_WRITE_TOKEN`. Drop the `models-service-account`. `terraform.tfvars` declares the notes
service: one server `rest`, one listener `summarize_note` on `NoteCreated`, one executor
`summarize_note`, one job `purge_notes`, the three standard triggers, and the
`acknowledge_command_result` listener.

**admin, mcp, web**: copy, replace domain and project placeholders, rename the Vercel project to
`${feature_environment}acme-web`, drop the Google Picker and Posthog environment entries.

**CLI**: copy `_bin/m` (guard renamed to `app-template`, and documented in `rename.md` as the one
line that changes with the folder name), `Makefile` (drop build-mobile, submit-mobile, landing,
docs, scripts, export-widget-schema, agentic-coding targets), `code-quality/*`, `deployment/*`,
`env-setup/*` (init loses the scripts sync), `local/*` minus landing, docs, script, nb.
`_helpers`: keep `agent_parity`, `get_changed`, `get_service_components`, `get_token`,
`generate_openapi`, the feature environment scripts, `clear_feature_cache`, `clear_feature_clerk`,
`clear_feature_storage`, `delete_feature_database`, `purge_feature_tasks`, `list_*`. Drop
`clear_feature_neo4j`, `clear_feature_vectors`, `validate_data`.

**Docker**: copy all three. Services Dockerfile loses the nltk step.

**Workflows**: copy `pull-request-checks`, `deployment`, `create-feature-environment`,
`destroy-feature-environment`, `mobile-deployment`. Drop `demo-seed`. Secrets reduce to
`CLERK_SECRET_KEY`, `GEMINI_API_KEY`, `EXPO_TOKEN`.

Gate: `terraform init -backend=false && terraform validate` in all five configurations.

## Phase 2: library

Copy `library/`, then prune to the kernel.

**Keep**: `domain/{aggregates,entities,errors,outbox,queries,repositories,services}.py`,
`domain/commands/base.py`, `domain/events/{base,common}.py`, `domain/value_objects/{core,common,
users,llm}.py`, `domain/audit/**`, `application/{auth,cache,errors,events,triggers,unit_of_work,
users}.py`, `application/audit/**`, `infrastructure/{concurrency,errors,outbox,repository,sentry,
service,unit_of_work,users}.py`, `infrastructure/cloud/**` (minus `bigquery.py` if nothing reads it
after pruning), `infrastructure/llm/{models,prompt,run,settings,telemetry}.py`,
`infrastructure/persistence/**`, `infrastructure/audit/**`, `presentation/**`, `_testutils/**`,
`logs.py`.

**Drop**: `domain/commands/{alignment,assets,audience,content}.py`, `domain/events/{alignment,
assets,audience,content}.py`, `domain/value_objects/{alignment,article,assets,audience,concept,
context,conversation}.py`, `domain/interfaces/**`, `infrastructure/services/**`,
`infrastructure/chunkdown`, `infrastructure/llm/{publish,vertical}.py`, `_opensource`,
`integrations`, `application/{quota,vertical}.py`.

**Add**: `domain/commands/notes.py` (`SummarizeNote`), `domain/events/notes.py` (`NoteCreated`,
`NoteSummarized`), `domain/value_objects/notes.py` (`NoteID`). Cross-service contracts live in the
library in Mention, so the scaffold keeps that convention even with one service.

**Dependencies**: drop `boto3`, `cohere`, `neo4j`, `nltk`, `numpy`, `pyahocorasick`, `marko`,
`base58` unless a kept module imports it (check with `uv run python -c import` per module).

**Tests**: keep `_testutils`, `application/{audit,test_auth,test_message_parser}`,
`domain/audit`, `domain/value_objects/{test_core,test_common,test_users}`, `infrastructure/{audit,
cloud,llm minus test_vertical and test_publish,persistence,test_repository,test_sentry,
test_unit_of_work,test_users}`, `presentation/*`. Rewrite `domain/events/test_*.py` as one test
for the notes events.

Gate: `m init`, `m run-code-formatting`, `m test-library`, pyright clean on `library/`.

## Phase 3: services/notes

`services/notes/notes_service/`, one aggregate, every component type once.

```
domain/aggregates/note/{aggregate,value_objects}.py   Note: create, record_summary, purge rules
domain/repositories.py                                INoteRepository
domain/interfaces/summarizer.py                       ISummarizer
application/notes/dtos.py
application/notes/use_cases/{create,summarize,list,purge}.py
infrastructure/persistence/notes.py                   Firestore repository
infrastructure/queries/notes.py                       list query
infrastructure/services/summarizer/{service,models}.py  pydantic-ai through library.infrastructure.llm
presentation/dependencies/{repositories,queries,infrastructure_services,use_cases/notes}.py
presentation/servers/rest/app.py + routers/notes/{routes,models}.py
presentation/listeners/{acknowledge_command_result,summarize_note}.py
presentation/executors/summarize_note.py
presentation/jobs/purge_notes.py
```

`pyproject.toml` scripts: `run-server-rest`, `run-listener-acknowledge_command_result`,
`run-listener-summarize_note`, `run-executor-summarize_note`, `run-job-purge_notes`,
`run-trigger-publish_event`, `run-trigger-submit_command`, `run-trigger-publish_audit_event`.

Tests mirror Mention's `python-service-tests` rule: domain aggregate tests, use case tests with
the in-memory repository and fake dispatcher from `_testutils`, one REST route test, a stub
summarizer.

Gate: `m test-service-notes`, `m run-checks-backend`, `m build-service-notes` produces an image.

## Phase 4: admin

Copy `admin/`, keep `server` (routers `backfills`, `runs`, `operations`, `organizations`, `seed`),
`client`, `common` (drop `store_shapes.py` if only copy used it), `backfill` (`commands`,
`registry`, `migrations/` with one example that stamps a new field on notes). `seed` reduces to
`commands`, `runner`, `auth`, `clients`, `state`, and one phase that creates a Clerk org, a user,
and three notes over the REST API. Drop `copy`, `credits`, and their routers and Cloud Run jobs
from `admin.tf`.

Gate: `m test-admin`, `m build-admin`.

## Phase 5: packages and web

1. `packages/acme-api`: `m compile-api` generates `src/api.d.ts` from the notes service.
2. `packages/acme-api-client`: keep the client factory, query keys, and hook shape; drop every
   Mention query factory; add `notes` queries and the create mutation.
3. `apps/web`: keep `main.tsx`, `__root.tsx`, the Clerk provider, the org switcher route, the
   api-client wiring, `components/ui` (shadcn primitives actually imported), `page-states`,
   `lib/{api,errors,utils}`. Routes: `/` (org guard), `/notes` (list + create form + summary
   status), `/switcher`. Drop everything else. `package.json` drops lamejs, MCP SDK, xstate,
   markdown and katex plugins, day-picker, virtual, cmdk, posthog, vaul, widgets.

Gate: `m run-checks-frontend`, `m run-web` against a feature environment shows the notes page.

## Phase 6: mobile and mcp

**mobile**: keep `_layout.tsx`, `index.tsx`, `sign-in.tsx`, `lib/{api,clerk,errors,finish-sign-in,
oauth,theme,roles}`, `components/{error-boundary,sign-out-link,sso-buttons,ui}`. Add
`(member)/notes.tsx`. `app.json` and `eas.json` carry `acme` placeholders, no Apple or Play ids.
Drop push, notifications, analytics, everything Mention-specific.

**mcp**: keep `index.ts`, `client.ts`, `instructions.ts`, `roles.ts`, `tools/index.ts`,
`tools/shared.ts`. Tools become `list_notes`, `create_note`. Package renamed `@acme/mcp`.

Gate: mobile `tsc --noEmit`, mcp `vitest run` and `tsup` build, `m run-checks-frontend`.

## Phase 7: agent guidance and docs

1. `.agents/rules/`: copy all, drop `mention-api-schema`, `public-docs`,
   `marketing-copy-no-em-dashes`. `rules.json` scopes updated. Add nothing.
2. `.agents/skills/`: keep `agent-parity`, `deploy-branch`, `review`, `verify`, `web-frontend`,
   `mobile-frontend`. Rename `investigate-mention-systems` to `investigate-systems` with product
   references removed.
3. `AGENTS.md`: Mention's minus the Mention MCP section and the public docs section, plus a
   pointer to `docs/bootstrap.md`. `CLAUDE.md` unchanged (`@AGENTS.md`).
4. `m sync-agent-parity` regenerates `.claude` and `.cursor`. `.claude/settings.json` copied.
5. `docs/bootstrap.md`: manual steps from the operations README, then the ordered terraform and
   deploy commands, then the secrets to create in Secret Manager per project, then Clerk, Vercel,
   and GitHub variables. `docs/rename.md`: the grep-derived list of files carrying `acme`, project
   ids, folder id, domain, Vercel team, and the `m` guard.
6. `README.md`: what this is, how to start a project from it (three paragraphs).

Gate: `m check-agent-parity`, `m run-checks`.

## Phase 8: deploy proof

On branch `deploy-proof`, real ids committed there and never merged.

1. Create GitHub repo `mention-ai-inc/app-template`, push `main`, mark as template.
2. GCP: folder `App Template` under org `490753959095`, project `acme-operations`, state bucket
   with 7 versions, `terraform` service account with the roles in `docs/bootstrap.md`, APIs
   enabled by hand. Set the ids in `terraform.tfvars` and the Makefile.
3. Mention repo: add NS record `acme.mentionai.app` to `operations/dns.tf` pointing at the new
   zone's name servers, apply with `m terraform-operations` from Mention. Separate small PR.
4. Clerk dev instance, keys into Secret Manager in both new projects and the environment module.
5. `m terraform-operations`, then `m terraform-services`, `m terraform-mcp`, `m terraform-admin`
   for the feature workspace, then `m deploy-notes`, `m deploy-mcp`, `m deploy-admin`,
   `m deploy-web` from a feature branch.
6. Verify end to end: sign in on the web app, create a note, watch `NoteCreated` reach the
   listener, the executor write the summary, the summary appear. Run the purge job by hand. Call
   `list_notes` through the MCP. Run the example backfill through the admin CLI.
7. Push a commit and confirm `pull-request-checks` and `deployment` workflows pass with the
   workload identity variables set.
8. Record anything the bootstrap doc got wrong, fix the doc on `main`.

## Phase 9: teardown

1. `terraform destroy` web, admin, mcp, services (feature and default workspaces), then
   operations. Delete the folder and the state bucket by hand.
2. Revert the NS record in Mention.
3. Delete the Clerk instance and the Vercel project if destroy left them.
4. Delete branch `deploy-proof`. `main` holds only placeholders.
5. Delete this file.

## Not built, on purpose

- No second service. `source_service_name` in the listener tfvars is where cross-service
  subscriptions go, and the library's commands and events packages already hold the convention.
- No landing page, docs site, extension, or widgets.
- No BigQuery domain-event views or scheduled queries.
- No mobile store configuration beyond the EAS profile skeleton.
- No rename script. `docs/rename.md` and `sed` cover it.
