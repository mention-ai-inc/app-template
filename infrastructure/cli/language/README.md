# Language CLI slot

This directory is a backend language slot. On `main` it holds only this file.

`main` is language-free: the `m` CLI, `admin`, and `control-plane` are Python tooling, but the
product backend (`library/`, `services/*`, `backfills/`) comes from a `lang/*` branch. Every base
script that needs to know about the backend looks here for a hook and does nothing when the hook is
absent, so the public `m` targets behave the same with or without a language installed.

A language branch adds:

| File | Contract |
| --- | --- |
| `project.json` | `{"language": "<l>"}`. |
| `targets.mk` | Language `m` targets (`test-library`, `test-service-%`, `test-backfills`, ...), pulled in by the `-include` at the end of `infrastructure/cli/Makefile`. |
| `envrc` | Sourced by `.envrc`; appends to `LANGUAGE_REQUIRED_PACKAGES` and adds language executables to `PATH`. |
| `init` | Run by `infrastructure/cli/env-setup/init` after the base environments exist; creates the language's environments. |
| `create-virtual-environment <name>` | Receives every name `infrastructure/cli/env-setup/create-virtual-environment` does not own (`main`, `control-plane`, `admin`). Without the hook that script fails with "no backend language installed". |
| `update-local-dependencies` | Run by `infrastructure/cli/env-setup/update-local-dependencies` after `control-plane` and the providers are refreshed. |
| `run-checks` | Run by `run-checks` and `run-checks-backend` while environments are prepared, before the base type check, format check and lint. Creates the language's environments and runs any check the base tools do not cover. |
| `run-tests-backend` | Run by `infrastructure/cli/code-quality/run-tests-backend` after the control-plane, provider and admin suites. Reads the change set as JSON from `CHANGED` (see `infrastructure/cli/_helpers/get_changed.py`) and exits non-zero when a suite fails. |
| `generate-openapi` | Prints the combined OpenAPI specification of every service to stdout; `m compile-api` turns it into `packages/acme-api/src/api.d.ts`. |
| `service-components` | Prints `{"<service>": {"server": [...], "pool": [...], "job": [...], "worker": [...]}}` for every service. |
| `helpers/` | Language-specific helpers used only by these scripts. |
| `pyright.json` | Python only: a partial pyright configuration whose `executionEnvironments` are merged into the git-ignored `/pyrightconfig.json` by `infrastructure/cli/_helpers/pyright_config.py`. |

The base files a language cannot add to use the same hooks: `pyproject.toml` ruff `src` globs cover
`library`, `services/*` and `backfills`; `pnpm-workspace.yaml` lists the same directories and pnpm
ignores a glob with no `package.json`; `.gitignore`, `.dockerignore` and `osv-scanner.toml` are
nested beside the files they govern instead of edited at the root.
