# Backfills image

This directory is a language slot. `main` holds only this README; the language branch adds the
`Dockerfile` that builds the `backfills` image for `backfills/`.

The image is what admin's `{env}admin-j-backfill` job runs, with the command `["backfill"]` and the
arguments the launch supplies (`list --json`, or `run <name> [--apply] [--organization-id <id>]`).
That command contract, described in `backfills/README.md`, is what lets the cloud branches build and
deploy the image without knowing which language wrote it: the recipe under
`infrastructure/docker/provider/backfills/` only names this `Dockerfile`.

The image installs `control-plane` and every provider under `control-plane/providers/*`, exactly as
the services image does, and nothing from `services/*`.
