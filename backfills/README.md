# Backfills

Schema-change backfills: the append-only, date-prefixed migrations that stamp new required fields
onto documents that already exist, run against an environment before the service code that needs
the field deploys (see the `no-schema-defaults` rule).

This directory is a language slot. `main` holds only this README; the language branch adds the
package, and the admin control plane launches it without knowing which language it is written in.

## The contract

The `backfills` image puts a `backfill` executable on `PATH`. Admin's `{env}admin-j-backfill` job
runs that image with the command `["backfill"]` and overrides only the arguments:

| Arguments | Behaviour |
| --- | --- |
| `list --json` | Print exactly one line `{"backfills": [{"name": "...", "description": "..."}, ...]}`. |
| `run <name> [--apply] [--organization-id <id>]` | Run one backfill. Dry run unless `--apply`. Exit non-zero on an unknown name. |

`FEATURE_ENVIRONMENT` names the environment (empty is production). A backfill reaches the stores
through the installed cloud provider's ports in `control-plane`; it imports no service package.

`GET /backfills` on the admin API and `m admin -- backfill list` launch `list --json` and read the
catalogue out of the execution's logs, so the deployed image is the source of truth for what can
run. `m admin -- backfill run <name>` launches `run` with the same arguments.

## Python

`pyproject.toml` builds the `backfills` distribution (`backfill = "backfills.cli:app"`). Modules
under `backfills/migrations/` expose a module-level `BACKFILL = Backfill(name=..., description=...,
run=_run)`; `registry.discover()` imports them in filename order, so a new migration is data, not a
new command. `run` takes keyword-only `environment`, `apply`, and `organization_id`.

`20260911_note_word_count.py` is the reference shape: the provider document store against a
permissive local model, idempotent, dry run by default, with its test in
`tests/test_note_word_count.py`.

```
m test-backfills
m admin -- backfill list
m admin -- backfill run note-word-count
m admin -- backfill run note-word-count --apply --organization-id org_XXXX
```

Locally, `m admin` runs the job as a subprocess of `backfills/.venv/bin/backfill` (or whatever
`BACKFILL_COMMAND` names). Deployed, the image is built by `m build-backfills` and shipped by
`m deploy-admin`.
