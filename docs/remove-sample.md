# Remove the sample

The scaffold's business logic is one sample service, `notes`, and it is wired into every layer so
that the whole pipeline is exercised on the first deploy. Remove it only after the first real
service is deployed end to end, so the repository is never without a working reference and the
`build-feature` skill always has a service to read. Do it in one branch.

Two things below are decisions, not deletions. Decide them first.

- **The membership-role cache key.** `library/library/application/auth.py` namespaces the
  organization membership cache under `Service.NOTES`. Point it at the service that owns users, or
  at whichever service every deployment includes.
- **The seed and token helpers.** `admin/admin/seed/clients.py`, `admin/admin/seed/auth.py`, and
  `infrastructure/cli/_helpers/get_token.py` call the notes REST server as the seeded service.
  Point them at the new service's REST server.

Find every remaining reference as you go:

```
git grep -n -i -E "notes?_service|services/notes|\bnotes?\b|NoteID|NoteCreated|NoteSummarized|SummarizeNote|Service\.NOTES" -- ':!pnpm-lock.yaml' ':!*/uv.lock' ':!docs/' ':!.agents' ':!.claude' ':!.cursor'
```

## 1. Surfaces

| File | What |
| --- | --- |
| `apps/mobile/app/(member)/notes.tsx` | Delete. Remove the tab from `(member)/_layout.tsx` and change the redirect in `app/index.tsx`. |
| `apps/web/src/routes/notes.tsx`, `apps/web/src/pages/notes/` | Delete. Change the redirect in `routes/index.tsx`. `routeTree.gen.ts` regenerates on the next build. |
| `apps/mcp/src/tools/notes.ts`, `notes.test.ts` | Delete. Remove the registration from `tools/index.ts` and rewrite `instructions.ts` and its test for the real product. |
| `packages/acme-api-client/src/queries/notes.ts`, `hooks/use-notes.ts` | Delete. Remove the exports from `index.ts` and the `notes` entry from `queries/keys.ts`. |

## 2. Admin

| File | What |
| --- | --- |
| `admin/admin/seed/phases/notes.py` | Delete. Remove the phase from `seed/runner.py` and fix the docstrings in `seed/commands.py` and `cli.py`. |
| `admin/admin/backfill/migrations/20260911_note_word_count.py`, `admin/tests/test_note_word_count.py` | Delete. This is the example backfill; write the first real one following its shape before removing it. |
| `admin/tests/server/test_jobs.py` | Uses a notes job name as a fixture string. Rename. |
| `admin/pyproject.toml` | Remove `notes_service` from dependencies and `[tool.uv.sources]`. |
| `infrastructure/docker/admin/Dockerfile` | Remove the three notes lines: the `pyproject.toml` copy, the loop entry, and the package copy. |

## 3. Infrastructure and workflow

| File | What |
| --- | --- |
| `infrastructure/terraform/configurations/services/terraform.tfvars` | Remove the `notes` entry from `services`. The `topics` block stays. |
| `.github/workflows/deployment.yaml` | Remove the `notes` input and its line in the "Deploy services to production" step. |

## 4. Shared kernel

| File | What |
| --- | --- |
| `library/library/domain/value_objects/notes.py`, `events/notes.py`, `commands/notes.py` | Delete. |
| `library/library/domain/value_objects/common.py` | Remove `NOTES` from the `Service` enum. |
| `library/library/infrastructure/persistence/storage.py` | Remove the notes entry from `SERVICE_BUCKETS`. |
| `library/tests/domain/events/test_notes.py` | Delete. |
| `library/tests/application/test_message_parser.py` | Rewrite against the new service's events. |
| `library/tests/_testutils/`, `library/tests/infrastructure/`, `library/tests/presentation/` | Six tests use `Service.NOTES` or the string `notes` as the `SERVICE` under test. Switch them to the new member. The `notes` field on the audit test widget is unrelated and stays. |

Follow `library-dependency-sync` after the change.

## 5. Repository tooling

| File | What |
| --- | --- |
| `pyproject.toml` (root) | Remove `notes_service` from `known-first-party`, the `services/notes` execution environment, and the two notes paths in the `infrastructure/cli/_helpers` environment. |
| `infrastructure/cli/_helpers/generate_openapi.py` | Remove `notes` from `SERVICES`. |
| `README.md` | Rewrite the "What is here" paragraph. |

## 6. Delete the service

```
git rm -r services/notes
m init
m run-code-formatting
m compile-api
m run-checks
```

## 7. Environments

Applying `m terraform-services` on a feature environment removes the notes pools, their schedulers,
their command queues, their change-feed triggers, and their event subscriptions. Removing the service
removes its pools outright, so no route survives it. Two things it leaves behind:

- Document collections prefixed `{env}notes_`, since collections are namespaced by name rather than
  declared. Delete them by hand if the environment is kept.
- Notes images in the branch's container registry and its build cache.

Production is the same, through the deployment workflow, on the merge that removes the entry.

## 8. Guidance that mentions notes

The rules under `.agents/rules/` and the review skill's standards use `Note` in their examples.
They are illustrative and stay valid. The `deployment-plan` rule and the `build-feature` skill name
`notes` as the scaffold's reference service; update both to name the service that replaced it, then
run `m sync-agent-parity` and `m check-agent-parity`.
