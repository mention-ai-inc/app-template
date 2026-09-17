# Start a new product

Choose a cloud, generate an independent repository, and deploy the notes web sample to a demo environment. Ask an agent to use `start-project`, or follow the same steps below yourself. The first milestone is signing in, creating an organization, saving a note, and seeing its summary.

## 1. Standalone beta and creation

Install uv, Git, and either Claude Code or Codex. Use the agent's own installation and
sign-in process; the launcher never collects agent credentials. Supported environments
are macOS and Linux, including WSL. Native Windows shells are not supported.

The beta package and template snapshots are public. Run from any directory:

```sh
uvx mention-template
```

The equivalent form is `uv run --no-project --with mention-template mention-template`.
For a reproducible version, use `uvx --from mention-template==0.1.0b2 mention-template`.
The launcher asks for agent, cloud, and destination, downloads a pinned snapshot, creates
the independent repository, and opens the agent in it. You can supply answers as flags:

```sh
uvx --from mention-template==0.1.0b2 mention-template --agent claude --cloud aws --directory ./my-product
uvx --from mention-template==0.1.0b2 mention-template resume ./my-product --agent codex
```

Resume preserves configuration and can switch agents. It starts a new conversation that
inspects actual progress. Missing agent installations produce guidance before any project
is created. Sign-in failures or exiting the agent leave the project available for resume.
This beta does not establish successful live cloud onboarding; see `docs/setup-verification.md`.
Contributors can also create projects directly from their checkout using the route below.

### Contributor route from a checkout

Supported developer environments are macOS and Linux, including WSL. Native Windows shells are not supported. Install Git, Python 3.9 or newer, and GNU Make first (on macOS, GNU Make is usually named `gmake`). Configure your Git author identity before your first commit.

Clone this template with its cloud branches available, then run from the template checkout:

```sh
./infrastructure/cli/_bin/m new-project -- --cloud aws --directory ../my-product
```

Choose `gcp`, `aws`, or `azure`. The destination must be absent or empty and outside the template checkout. If the cloud branch is unavailable, fetch it from the template remote first. The command exports the selected committed revision, creates a fresh Git repository on `main`, and records its origin in `project.json`. Uncommitted template edits are not included. No remote is configured and nothing is published or deployed.

Continue all subsequent steps inside the new repository. Its `main` contains the selected provider. Edit application and infrastructure files normally; this template's rules for maintaining multiple cloud branches do not apply to your product. Future template changes are adopted selectively, without a promised upstream merge workflow.

## 2. Project identity and local tools

Edit `project.json`: set the slug, display name, domain (for example `product.example.com`), and GitHub `owner/repository`. Provider field descriptions live in `infrastructure/cli/provider/project.json`. Leave values that you do not have yet empty; fill them as the cloud guide produces them. Do not put tokens, passwords, private keys, or secret values in this file.

Install GNU Make and Python 3.9 or newer for repository commands, Node 22 or newer, pnpm 10 (the version is pinned in package.json), uv, and optionally direnv. uv installs the project's Python 3.13 environment. Cloud deployment additionally requires Terraform, jq, Docker with buildx, and your provider CLI; follow the provider guide before using them.

```sh
./infrastructure/cli/_bin/m configure-project
./infrastructure/cli/_bin/m configure-project -- --apply
./infrastructure/cli/_bin/m doctor -- --stage local
```

Preview performs no writes. Apply renames packages and configured references, regenerates dependencies and API clients, and synchronizes agent guidance. Review its diff. Repeat after changing project.json; unchanged inputs are a no-op. If an existing file conflicts, reconcile it rather than discarding product work. An interrupted apply can be retried. The committed `.project-template.json` stores original template text and managed-file hashes for this purpose; it contains no credentials.

Without direnv, keep using the checked-in executable or add `infrastructure/cli/_bin` to PATH. With direnv installed and its shell hook configured, run `direnv allow`. Copy `.env.example` to ignored `.env` only if you need local application credentials. Do not commit `.env`.

Create an empty GitHub repository, review and commit the generated project, add its remote, and push `main`. GitHub publication is a separate user action. The configured repository name must match the repository that will run CI.

## 3. Cloud foundation

Follow `docs/bootstrap.md` on your selected cloud. It identifies the manual account, billing, initial identity, Terraform state, and DNS steps. Keep external account creation and secret entry in the respective consoles. Credentials are never supplied in a chat transcript.

Run `m doctor -- --stage cloud` as you configure identifiers. It uses read-only provider checks and prints next actions. Missing identifiers, permissions, or tools block only the relevant stage. Some values become available after operations provisioning; return to project.json and apply them then.

The first deployment needs Clerk, Gemini, Vercel, and cloud infrastructure. Sentry, Logfire, admin, MCP, and mobile credentials are unnecessary while those integrations are disabled. Infrastructure still incurs the provider's normal resource charges; inspect the Terraform plan before applying it.

## 4. Clerk and first-user setup

Create a Clerk application with organizations enabled. Start with its development instance for demo. Put its publishable key and full JWKS URL in `clerk.feature` in project.json. Store its secret key as described by the cloud guide. The notes sample does not require a webhook. Production will use separate values later.

The web app requests a JWT template named `main`. Configure that template to supply these claims using Clerk's user and active-organization fields:

```json
{
  "uid": "{{user.id}}",
  "organization_id": "{{org.id}}",
  "clerk_role": "{{org.role}}",
  "organization_public_metadata": "{{org.public_metadata}}"
}
```

Preserve standard token time claims and use the instance's normal signing keys. Organization public metadata must be an object (an empty object is sufficient for the sample). Preview a token in Clerk and verify these claims before testing API requests. `clerk_role` must resolve to `org:admin` or `org:member`.

Enable the sign-in/sign-up method you intend to use. Visit demo, sign in, and create or select an organization using the organization picker. Do not bypass authentication or use an unsigned local token to verify deployment. Configure production DNS and instance keys only when preparing production.

## 5. Deploy and verify demo

Complete the cloud-specific secret and DNS steps, then preview infrastructure with the provider's `terraform-plan-*` targets. After authorizing deployment:

```sh
FEATURE_ENVIRONMENT=demo m create-feature-environment
m doctor -- --stage demo
```

Creation deploys services and the configured surfaces. Health polling stops after ten minutes with an error; inspect the deployment logs and retry after fixing the cause. Terraform or build failures must stop the sequence.

Open the web URL reported by deployment. Sign in, select an organization, create a note, and wait for a nonempty summary. Reload to verify persistence. Record the revision and actual results in `docs/setup-verification.md`; health checks alone are not a successful walkthrough.

For a failed deployment, retain the environment while diagnosing. To remove demo when you are ready:

```sh
FEATURE_ENVIRONMENT=demo m destroy-feature-environment
```

This deletes that environment's data. Shared operations resources and manually created state storage require separate, deliberate cleanup described by the cloud guide.

## 6. Continue building

Fill in the product overview and requirements, use `define-design` for your brand and application design, and build the first real service before removing notes. Optional surfaces and monitoring are enabled in project.json, followed by configure-project and their documented account/secret setup. Disabling a previously deployed surface does not delete its resources; destroy that surface before disabling it.

PR merges deploy configured surfaces to demo by default. Set `deployment.auto_demo` to `false` in project.json to pause automatic demo deployment; omitted settings preserve the default. The Deployment workflow also accepts an explicit `environment=demo` dispatch while paused. Manual dispatch defaults to production for compatibility. A partial manual demo deployment does not advance the full demo deployment baseline. Production is an explicit workflow dispatch: first configure `clerk.production`, the production secrets and DNS, and any enabled integrations. `EXPO_TOKEN` and store accounts are only needed when enabling mobile distribution.
