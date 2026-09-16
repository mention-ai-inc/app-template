# Configure AZURE identifiers

Use `project.json` and `m configure-project`; do not globally replace identifiers. The exact fields,
formats, descriptions, file scopes, and read-only checks live in `infrastructure/cli/provider/project.json`.
Follow `docs/bootstrap.md` for the order in which identifiers become available. Initial identity and
state storage are manual foundation steps; project configuration itself does not create cloud resources.

An empty field remains provisional and is reported by the appropriate doctor stage. Preserve protocol
constants such as Azure's token-login username. Product domains and repository references are shared
configuration fields. Clerk JWKS URLs are explicit per environment rather than inferred from cloud ids.
