# Provider image builds

This directory is a cloud provider slot. On `main` it holds only this file.

The `Dockerfile` for each component is portable and lives on `main` at
`infrastructure/docker/<component>/Dockerfile`. Only the build-and-push recipe is provider-specific:
a cloud branch adds `<component>/` here for `services`, `mcp`, and `admin`.

See `docs/cloud-providers.md`.
