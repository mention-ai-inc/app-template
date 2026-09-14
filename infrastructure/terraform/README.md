# Terraform

This directory is a cloud provider slot. On `main` it holds only this file; the modules and
configurations come from the `cloud/*` branch you are on.

Every cloud branch must expose these configuration names, because
`infrastructure/cli/provider/deployment/run-terraform` and the `m terraform-*` targets address them
by name: `operations`, `services`, `web`, `mcp`, `admin`.

See `docs/cloud-providers.md`.
