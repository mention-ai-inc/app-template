# Provider CLI slot

This directory is a cloud provider slot. On `main` it holds only this file.

A cloud branch adds:

- `targets.mk` — deployment `m` targets, pulled in by the `-include` at the end of
  `infrastructure/cli/Makefile`.
- `deployment/` — the scripts those targets run.
- `helpers/` — provider-specific helpers used only by those scripts.
- `envrc` — sourced by `.envrc`; sets credentials, adds the provider SDK to `PATH`, and appends to
  `PROVIDER_REQUIRED_PACKAGES`.
- `feature-environment` — sourced by `infrastructure/cli/_helpers/set-feature-environment`; maps
  `$FEATURE_ENVIRONMENT` onto a provider account or project.

Each hook is optional in the sense that base tolerates its absence, and required in the sense that
deployment does not work without it. See `docs/cloud-providers.md`.
