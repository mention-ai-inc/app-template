---
name: verify
description: How to run and observe this repo's web app and feature-environment API for runtime verification.
---

# Verifying changes at runtime

## Web app (apps/web)

- Launch: `m run-web` (or `cd apps/web && pnpm dev --port <port>`); it sources `infrastructure/cli/_helpers/set-feature-environment`, deriving `FEATURE_ENVIRONMENT` from the branch name with dashes stripped (`issue-297` → `issue297`). A stale `FEATURE_ENVIRONMENT` shell export silently overrides this — pin it explicitly.
- The app requires Clerk sign-in; there is no headless auth path and no Playwright/puppeteer in the repo, so pixel-level GUI verification needs a human with a browser session.
- Module-level runtime smoke check without a browser: fetch transformed modules from Vite, e.g. `curl http://localhost:<port>/src/components/<file>.tsx` — 200 with no `Failed to resolve` in the body proves the import graph (including `@packages/*` workspace packages) resolves. Workspace package internals resolve via `/@fs/...` URLs found in the importing module's output.
- lucide-react resolves from the repo-root `node_modules/lucide-react` (pnpm hoisted); to check icon names exist: `node -e "require('<repo>/node_modules/lucide-react/dist/cjs/lucide-react.js')"`.

## Feature-environment API

- Base URL: `https://<env>api.<domain>`; per-service OpenAPI spec at `/rest/<service>/openapi` (NOT `openapi.json`), Swagger UI at `/rest/<service>/docs`. Use the spec to confirm routes are deployed.
- There is no working way to mint an auth token from the CLI (`m get-token` is defunct — deployed services reject its impersonation tokens). Authenticated API driving requires a token from a real signed-in session; without one, limit verification to unauthenticated surfaces (OpenAPI spec, 401 behavior).
