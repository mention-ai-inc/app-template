# Rename

The scaffold ships under the placeholder product name `acme` with fake ids everywhere a real one is
needed. Work through this file top to bottom before the first `terraform apply`. Each section
gives the placeholder, where it lives, and a command that finds every occurrence.

## 1. Product name `acme`

Package and app names, the API base URL prefix, display names, and whatever your cloud names after
the product — projects, buckets, resource groups, registries — all derive from it.

```
git grep -n -i acme -- ':!pnpm-lock.yaml' ':!uv.lock' ':!*/uv.lock' ':!docs/'
```

Rename these directories too: `packages/acme-api`, `packages/acme-api-client`. Then run
`m init` so the lockfiles pick up the new package names, and `m compile-api`.

Display names to set by hand: `apps/mobile/app.json` (`name`, `slug`, `scheme`),
`apps/mcp/src/index.ts` (server name), `apps/web/index.html` (title), the root `description`
fields in `package.json` and `pyproject.toml`, and the H1 and opening paragraph of `README.md`.

## 2. Account, project, and subscription ids

What these are called depends on the cloud — projects on GCP, accounts on AWS, subscriptions and
resource groups on Azure — so **`docs/rename.provider.md` on this branch owns this step**. Work
through it before coming back here.

Every branch spells its placeholders the same way, so this finds them wherever they live:

```
git grep -n -E "acme-(operations|production|feature)-0000|0{12}|00000000-0000-0000-0000-0{12}"
```

One thing that step leaves behind, because it is a `main` file and easy to miss:
`library/library/presentation/auth/direct.py` keys `JWK_DOMAINS_BY_DEPLOYMENT` by **deployment id** —
whatever `IRuntimeContext.get_deployment_id()` returns on your cloud. Change the keys as well as the
URLs, or every request fails with "no identity provider JWKS host is configured for deployment".

## 3. Domain and DNS zone

Placeholders: `acme.example.com`, zone name `acme`.

```
git grep -n -E "acme\.example\.com|dns_managed_zone"
```

| File | What |
| --- | --- |
| `infrastructure/terraform/configurations/operations/dns.tf` | the managed zone |
| `infrastructure/terraform/configurations/{services,admin,mcp,web}/terraform.tfvars` | `domain_name`, `app_domain`, and whichever DNS zone variable your branch takes |
| `infrastructure/terraform/configurations/services/monitoring.tf` | alert notification email |
| `infrastructure/terraform/modules/permissions/main.tf` | engineer emails |
| `library/library/conventions.py` | `DOMAIN` and `APP_DOMAIN` |
| `library/library/presentation/auth/direct.py` | Clerk JWKS hosts |
| `apps/web/src/main.tsx`, `apps/mobile/lib/api.ts`, `apps/mcp/src/index.ts` | API base URL |
| `infrastructure/cli/provider/deployment/create-feature-environment` | health check URL |
| `admin/README.md`, `admin/tests/server/*.py`, `library/tests/**` | example hosts and emails in tests and docs |

## 4. Clerk

Placeholders: `pk_test_REPLACE_ME`, `pk_live_REPLACE_ME`.

| File | What |
| --- | --- |
| `infrastructure/terraform/modules/environment/{feature,production}.tf` | publishable keys |
| `library/library/presentation/auth/direct.py` | JWKS URLs of the two instances (`your-instance.clerk.accounts.dev` for the dev instance) |
| `infrastructure/terraform/configurations/operations/dns.tf` | production instance DNS records, added once Clerk issues them |

Secret keys never live in the repo; see `docs/bootstrap.md`.

## 5. Vercel

Placeholder: `team_0000000000000000` in `infrastructure/terraform/configurations/web/terraform.tfvars`.
The project name is `${feature_environment}acme-web` in `web/vercel.tf` and follows the product
name.

## 6. GitHub repository

Placeholder: `mention-ai-inc/app-template` as `github_repo` in the `operations`, `services`, and
`web` `terraform.tfvars`. Whatever your branch federates CI with — a workload identity pool, an OIDC
role, a federated credential — trusts exactly that repository and nothing else.

## 7. The `m` guard

`infrastructure/cli/_bin/m` refuses to run unless the directory holding the main checkout's `.git`
(a worktree resolves to its main checkout) has the name the guard compares against. Change that
string to the new folder name.

## 8. Verify

```
m init
m run-checks
m run-checks-frontend
m run-tests-backend
m test-admin
```

`m run-checks` runs no test suite; `m run-checks-frontend` runs the MCP tests, and the last two run
the Python suites.

Then continue with `docs/bootstrap.md`.
