# Provider slot

`library` declares ports and never imports a cloud. Each cloud's adapters are a distribution of
their own in this directory, depending on `library` and on that cloud's SDKs, so
`library/pyproject.toml` — a `main` file a cloud branch may not edit — stays free of them.

```
library/providers/<cloud>/
  pyproject.toml              name "library-provider-<cloud>", package library_provider_<cloud>
  library_provider_<cloud>/   the adapters
  tests/                      the distribution's own suite
```

A provider is selected by what is installed, not by configuration. Each distribution registers
itself:

```toml
[project.entry-points."acme.cloud_provider"]
<cloud> = "library_provider_<cloud>.provider:PROVIDER"
```

`library/library/providers/registry.py` resolves that group with `importlib.metadata`. With nothing
installed it falls back to the built-in `local` provider; with exactly one installed it uses that
one; with more than one, `CLOUD_PROVIDER` says which.

Everything that installs a Python environment loops over this directory and installs whatever it
finds — `infrastructure/cli/env-setup/create-virtual-environment`,
`infrastructure/cli/env-setup/update-local-dependencies`, `infrastructure/docker/services/Dockerfile`,
and `infrastructure/docker/admin/Dockerfile`. Every one of those loops is a no-op when the directory
holds only this file, which is what `main` looks like once `docs/ports-and-adapters.md` stage 6 has
moved `gcp/` onto `cloud/gcp`.

Adding a cloud means adding a directory here on that cloud's branch. `docs/ports-and-adapters.md`
section 4 has the full rationale, and the conformance suite under
`library/tests/application/ports/conformance/` is the definition of done.
