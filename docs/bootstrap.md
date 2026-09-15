# Bootstrap

How a fresh copy of this scaffold becomes a deployed product on Azure. Every id below is a placeholder
until you finish `docs/rename.md`; do that first.

Feature environments are **name-prefixed resources in one subscription**, not subscriptions of their
own. There is one Azure subscription, one Entra ID tenant, three resource groups — operations,
production, feature — and one DNS zone; `production` is the `default` Terraform workspace and every
feature environment is a workspace whose name becomes the prefix on everything it creates.

Globally unique names are the thing Azure makes you think about that the other clouds do not. A
storage account, a key vault, a container registry, a Service Bus namespace and a Cosmos DB account
all share one global namespace, so the `0000` suffix in every placeholder is there to be replaced with
something nobody else has taken.

## 1. Azure, by hand

Terraform cannot create the subscription it runs in, the storage account it keeps its state in, or the
identity it uses to do either. Those come first, manually, exactly once.

1. Create or pick the subscription, and note its id and its tenant id. They replace
   `00000000-0000-0000-0000-000000000000` throughout the Terraform, in every configuration's
   `base.tf` backend block, and in `infrastructure/cli/provider/targets.mk`.
2. Create the operations resource group `acme-operations-0000` in the deployment region. It is the
   only resource group Terraform treats as pre-existing (`data "azurerm_resource_group" "operations"`);
   the production and feature groups are created by the first apply.
3. Create a storage account named `acmeoperations0000tf` in that group, with a blob container named
   `terraform-state`. Turn on versioning and blob soft delete, turn off public blob access, and leave
   shared-key access enabled **or** grant yourself Storage Blob Data Contributor on it — the backend
   is configured with `use_azuread_auth = true`, so it authenticates as you, not with a key. State
   locking uses blob leases; there is no separate lock table to create. The account name is repeated
   in every configuration's `base.tf`.
4. Grant yourself, for the first apply only, roles that Owner does not imply because they are
   data-plane rather than control-plane: **Key Vault Secrets Officer** and **Key Vault Crypto Officer**
   at the subscription scope. Terraform writes secrets and creates the per-service signing keys through
   the vault's data plane, and an RBAC-authorized vault refuses both to a principal that only holds
   Owner.
5. Put a real engineer in `infrastructure/terraform/modules/permissions/main.tf` — both the sign-in
   address and the directory **object id**. Azure role assignments address principals by object id, and
   an assignment to one that does not exist fails the first apply half way through.
6. Fill `infrastructure/terraform/configurations/operations/terraform.tfvars` with the subscription id,
   the tenant id, the resource group names, the globally unique resource names, the GitHub repository,
   the region, and the domain.

## 2. Quotas and registrations

Raise or check these before the first real deploy, not after it fails:

- **Resource providers.** A new subscription has most of them unregistered. Register
  `Microsoft.App`, `Microsoft.ContainerRegistry`, `Microsoft.DocumentDB`, `Microsoft.ServiceBus`,
  `Microsoft.Cache`, `Microsoft.KeyVault`, `Microsoft.OperationalInsights`, `Microsoft.Cdn` and
  `Microsoft.Network` with `az provider register --namespace <name>`. Registration is asynchronous and
  the first apply fails outright against an unregistered provider.
- **Container Apps cores** in the deployment region. The default is small enough that one feature
  environment plus production exhausts it.
- **Cosmos DB accounts per subscription**, which defaults to 50 but counts the serverless feature
  account as one of them.
- The `containerapp` extension for the CLI. `infrastructure/cli/provider/envrc` installs it on
  `direnv allow`, and every deployment script re-checks, but CI installs it explicitly.

## 3. Domain

`operations/dns.tf` creates the DNS zone for `domain_name`. After the first `m terraform-operations`,
point the registrar's NS records at the zone's name servers (`terraform output dns_zone_name_servers`),
or add an NS record in the parent zone if you are delegating a subdomain. Do this **before** anything
asks for a certificate: both Container Apps managed certificates and Front Door custom domains validate
by DNS and will sit in `Pending` forever otherwise.

## 4. Local setup

```
direnv allow
m init
az login
az account set --subscription 00000000-0000-0000-0000-000000000000
```

`infrastructure/cli/provider/envrc` sets the region, subscription and tenant, and points Terraform's
`ARM_*` variables at the same values; `az` must be on `PATH` (`PROVIDER_REQUIRED_PACKAGES` warns if it
is not). You also need Docker with `buildx`, because images build locally and push straight to the
container registry.

## 5. Operations configuration

```
m terraform-operations
```

This creates the production and feature resource groups, the container registry, the three key vaults,
the three storage accounts and the `static-assets` container, the two Service Bus namespaces, the two
Cosmos DB accounts, the two Log Analytics workspaces and Container App Environments, the two Front Door
profiles, the DNS zone, the engineers' role assignments, and the two Entra ID application registrations
with their GitHub federated credentials. Operations always applies in the `default` workspace; the
target does not take a feature environment.

The apply prints the resource group ids, both Container App Environment ids, the registry login server,
and the `github_actions_client_id` and `terraform_client_id` that CI needs. Nothing downstream needs
copying by hand — the other configurations read them through `terraform_remote_state`.

If a configuration was ever initialised with `-backend=false`, delete its `.terraform` directory before
the first real apply.

## 6. Secrets, by hand

Terraform reads these from Key Vault and never creates them. Create each one once, with a real value —
a secret with no version fails the data source at plan time. Key Vault secret names allow letters,
digits and hyphens only, which is why every variable is spelled with hyphens here and underscores in
the container.

| Secret | Vault | Used by |
| --- | --- | --- |
| `CLERK-SECRET-KEY` | production, feature | services, admin, mcp, web |
| `CLERK-WEBHOOK-SECRET` | production, feature | services, admin |
| `GEMINI-API-KEY` | production, feature | services, admin |
| `LOGFIRE-WRITE-TOKEN` | production, feature | services, admin |
| `SENTRY-DSN` | operations | services, admin |
| `VERCEL-TERRAFORM-API-KEY` | operations | web terraform |

`<environment>-REDIS-PASSWORD` is written by the services configuration from the cache's own access
key; do not create it by hand. The per-service signing keys (`<environment><service>-s-signing`) are
Key Vault *keys*, not secrets, and the services configuration creates them.

The admin API has no identity-aware proxy in front of it — Container Apps has no such thing. The outer
gate is the ingress IP allowlist in `configurations/admin/terraform.tfvars`, and the inner one is the
Entra ID token the application validates against the app registration `configurations/admin/entra.tf`
creates. Fill `admin_ip_allowlist` before exposing it, or the allowlist is empty and the ingress is
open to anyone who then has to pass the token check.

## 7. Clerk

Create a Clerk application with organizations enabled and two instances: development (feature
environments) and production. Put the publishable keys in
`infrastructure/terraform/modules/environment/{feature,production}.tf`, the secret key in the matching
key vault as above, and the production instance's DNS records in `operations/dns.tf` once you have
them. The webhook secret comes from a Clerk webhook pointed at the services API.

## 8. Vercel

Create or pick a team, put its id in `configurations/web/terraform.tfvars`, and store a team token in
the operations key vault as `VERCEL-TERRAFORM-API-KEY`. Terraform creates the project and the
deployment, and `web/dns.tf` adds the CNAME in the Azure DNS zone.

## 9. Feature environment

From a branch (the branch name, with hyphens stripped, becomes the Terraform workspace and the
`FEATURE_ENVIRONMENT` prefix):

```
m terraform-services
m terraform-mcp
m terraform-admin
m deploy-notes
m deploy-admin
m deploy-mcp
m deploy-web
```

Or `m create-feature-environment`, which runs the same sequence and then waits on
`https://<environment>api.<domain>/rest/<service>/health`.

Three things about the first apply in a new workspace:

- Every Container App and job comes up on whatever the image reference resolves to, which before the
  first deploy is nothing. It is the deploy that pushes a real image and points the app at it, so an
  app failing to pull before you have deployed is expected.
- Front Door custom-domain validation adds a TXT record and then waits. If the DNS zone is not yet
  delegated (step 3) this is where the apply hangs. The endpoint's own
  `<endpoint>.azurefd.net` hostname serves the same routes in the meantime, and the services
  configuration outputs it as `front_door_endpoint_host_name`.
- The feature Cosmos DB account is serverless, so `cosmos_max_throughput` does not apply there and
  the change feed lease containers are created without provisioned throughput.

## 10. GitHub

Repository variables:

- `AZURE_CLIENT_ID` — `terraform_client_id` from the operations apply
- `AZURE_TENANT_ID` — the tenant id
- `AZURE_SUBSCRIPTION_ID` — the subscription id

Repository secrets: `CLERK_SECRET_KEY`, `GEMINI_API_KEY`, `EXPO_TOKEN`.

There are **no Azure client secrets**. Every workflow authenticates with `azure/login@v2` against the
federated credentials created in the operations configuration, which pin the issuer, the audience
`api://AzureADTokenExchange`, and the exact subject — `repo:<owner>/<repo>:ref:refs/heads/main`,
`repo:<owner>/<repo>:pull_request`, and `repo:<owner>/<repo>:environment:production`. Entra matches a
subject exactly, so a workflow running on any other ref cannot authenticate at all; add a credential
rather than loosening one. Set `github_repo` in the tfvars to the real repository before that apply,
or CI can exchange nothing. Each job that authenticates needs `permissions: id-token: write`.

`pull-request-checks` and `pull-request-cloud-checks` run on every PR. `create-feature-environment` and
`destroy-feature-environment` are manual triggers. The `deployment` workflow runs when a PR into `main`
is merged: it deploys to a long-lived feature environment named `demo`, and it can also be dispatched by
hand per surface to ship production.

## 11. Production

Merge to `main`. The `deployment` workflow does the rest. The first run needs the `demo` feature
environment to exist, so create it once from a branch named `demo` with `m create-feature-environment`.
