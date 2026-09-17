---
name: start-project
description: Guides a newcomer from choosing a cloud to creating an independent product repository and deploying the web sample. Uses the project setup CLI and resumes from configuration and diagnostic results. Use when starting a product from this template or continuing its initial setup.
---

# Start a product

Read `docs/getting-started.md`. The first milestone is a signed-in user creating a note and receiving its summary in demo. Production and optional integrations follow separately.

## Establish the project

Inspect the current directory first. If root `project.json` and `.project-template.json` exist, continue setup here, even if it has never been configured or this conversation uses a different agent. Read configuration and run the appropriate diagnostic stage before asking questions. Do not create another repository or replace it with a newer snapshot.

If no project exists, the published `mention-template` launcher asks for agent, cloud, and destination and opens the selected agent in the resulting repository. It uses an existing Claude Code or Codex installation and its own sign-in process. Never ask for an agent token in the conversation. See beta availability in `docs/getting-started.md`.

For a contributor in a template checkout, ask for cloud and destination if unknown, then use `m new-project -- --cloud <cloud> --directory <destination>`. This exports committed files into a fresh main branch, excluding local edits and upstream history. Never rename the template checkout in place.

Use `./infrastructure/cli/_bin/m` before shell integration is installed. Check Git, Python 3.9 or newer, and GNU Make before invoking repository commands. The launcher may have created this project before Make or application tools were installed.

Read `project.json` and ask only for missing decisions relevant to the next stage. Use the provider field descriptions in `infrastructure/cli/provider/project.json`. Keep credentials in ignored environment files or the provider secret store, never in chat, project.json, or the configuration snapshot.

Edit project.json, preview with `m configure-project`, and apply the agreed configuration with `m configure-project -- --apply`. Resolve reported conflicts with the user's intent; never overwrite manual edits to make the command pass. Rerunning apply recovers interrupted writes and retries incomplete regeneration.

## Work through the stages

1. Run `m doctor -- --stage local`. Resolve prerequisites before cloud work. Shell activation must not provision cloud resources.
2. Guide the user through reviewing, committing, and publishing the initial repository. New-project configures no remote and publishes nothing.
3. Read this cloud's `docs/bootstrap.md`. Guide the manual account, billing, identity, and state-storage steps in order. Distinguish chosen identifiers from outputs that do not exist yet.
4. Configure Clerk, Gemini, Vercel, and DNS using the guide. Run cloud diagnostics; describe exactly what remains manual. Do not print secret values when checking their presence.
5. Present the target account, demo environment, enabled surfaces, and Terraform plan using the provider's plan targets. Provision or deploy only when the user has requested that action; project creation alone is not deployment authorization.
6. Use `FEATURE_ENVIRONMENT=demo m create-feature-environment`. Run demo diagnostics, then guide the authenticated walkthrough. A healthy HTTP endpoint does not prove authentication, persistence, or summarization.
7. Record the tested revision and results in `docs/setup-verification.md`. Leave unavailable checks explicitly unverified. Guide cleanup when requested; do not destroy infrastructure merely because verification failed.

## Resume and extend

On a later invocation, inspect project.json, configuration transaction state, and the relevant doctor stage instead of repeating completed questions. Recover interrupted configuration with the existing apply command. `mention-template resume <directory> --agent claude|codex` starts a fresh guided conversation without requiring old chat history. Apply new configuration only when needed. Treat output and actual cloud state as evidence, not a remembered checklist.

Monitoring, admin, MCP, and mobile are disabled initially. Enable them only when requested, follow their setup prerequisites, and rerun configuration and checks. Production requires its own Clerk instance/configuration, secret setup, and an explicit workflow dispatch.

After the sample works, use the product overview and PRDs for requirements, `define-design` for brand and application design, and `build-feature` for the first real service. Keep the sample until its replacement is working. Do not rewrite product requirements or choose branding during infrastructure setup.
