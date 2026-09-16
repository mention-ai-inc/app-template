# Configure a product

Start with `docs/getting-started.md`. Generate a new repository from the chosen cloud before renaming anything; the template checkout is not the destination.

`project.json` is the nonsecret configuration input. Use `m configure-project` to preview changes and `m configure-project -- --apply` to apply them. The CLI updates package paths and imports, product names, domains, repository trust references, and the provider's declared identifier mappings. It regenerates dependencies, API clients, and agent mirrors using repository commands.

Provider fields and their validation patterns live in `infrastructure/cli/provider/project.json`; `docs/bootstrap.md` explains when each value becomes available. There is no global replacement of all-zero identifiers: some are protocol constants, such as Azure's registry token-login username.

Clerk's feature and production publishable keys and JWKS URLs are distinct fields. Secret keys stay in the provider secret store or an ignored local environment file. The runtime selects the JWKS URL from `CLERK_JWKS_URL`, not from an account/subscription identifier shared by multiple environments.

Review the generated diff before committing. Repeat configure-project when setup inputs change. Conflicting manual edits require reconciliation; the CLI will not overwrite them. If dependency installation or client generation fails, correct the error and repeat apply to finish regeneration.

After configuration, run formatting, checks, and tests through `m`; then continue with the selected cloud's bootstrap guide. The folder name is no longer an identity check for the CLI.
