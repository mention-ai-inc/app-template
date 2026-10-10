# Remove the sample

The scaffold's business logic is one sample service, `notes`, and it is wired into every layer so
that the whole pipeline is exercised on the first deploy. Remove it only after the first real
service is deployed end to end, so the repository is never without a working reference and the
`build-feature` skill always has a service to read. Do it in one branch.

Sections 4 and 6 are written per backend language. The language branch supplies
`docs/remove-sample.language.md` with the same section numbers, and a generated product always has
it; this file names only what is the same for every language.

Two things below are decisions, not deletions. Decide them first.

- **The membership-role cache key.** The kernel namespaces the organization membership cache under
  `Service.NOTES` (the file is named in `docs/remove-sample.language.md`). Point it at the service
  that owns users, or at whichever service every deployment includes.
- **The seed helpers.** `admin/admin/seed/clients.py` and `admin/admin/seed/auth.py` call the notes
  REST server as the seeded service. Point them at the new service's REST server.

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
| `admin/tests/server/test_jobs.py` | Uses a notes job name as a fixture string. Rename. |
| `backfills/` | The example backfill is the note word count; section 6 of `docs/remove-sample.language.md` names its files. Write the first real backfill following its shape before removing it. |

Admin depends on `control-plane` alone, so no dependency manifest or image recipe names the
service.

## 3. Infrastructure and workflow

| File | What |
| --- | --- |
| `infrastructure/terraform/configurations/services/terraform.tfvars` | Remove the `notes` entry from `services`. The `topics` block stays. |
| `.github/workflows/deployment.yaml` | Remove the `notes` input and its line in the "Deploy services to production" step. |

## 4. Shared kernel

| File | What |
| --- | --- |
| `control-plane/control_plane/domain/value_objects/common.py` | Remove `NOTES` from the `Service` enum. |
| `control-plane/control_plane/infrastructure/persistence/storage.py` | Remove the notes entry from `SERVICE_BUCKETS`. |
| `control-plane/tests/fixtures/documents/note.json` | The golden stored-document shape of a note. Replace it with the first real aggregate's shape; the test that asserts it lives with the service that owns the aggregate (section 6 of `docs/remove-sample.language.md`). |

Section 4 of `docs/remove-sample.language.md`: the notes value objects, events and commands in the
backend's kernel, and the kernel tests that use `notes` as the service under test.

Follow `library-dependency-sync` after the change.

## 5. Repository tooling

| File | What |
| --- | --- |
| `pyproject.toml` (root) | Nothing: the ruff `src` globs are generic. The type-checker environment for `services/notes` is section 5 of `docs/remove-sample.language.md`. |
| `packages/acme-api/openapi.json`, `packages/acme-api/src/api.d.ts` | Regenerate with `m compile-api` once the service is gone and commit both; `m check-api-contract` fails until they match. |
| `README.md` | Rewrite the "What is here" paragraph. |

## 6. Delete the service

Section 6 of `docs/remove-sample.language.md`: the package, the example backfill, and the
environments to recreate. Then:

```
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
They are illustrative and stay valid. The `deployment-plan` rule and the `build-feature` skill (and
its `LANGUAGE.md`) name `notes` as the scaffold's reference service; update them to name the
service that replaced it, then run `m sync-agent-parity` and `m check-agent-parity`.
