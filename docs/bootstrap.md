# Bootstrap on AZURE

Start with `docs/getting-started.md`. Generate a product repository and configure its identity before
following this guide. The selected cloud is already on your product's main branch. Keep project.json
as the nonsecret setup input and use configure-project after each group of new identifiers.

The foundation steps below are manual account setup. They are not performed by new-project or doctor.
A first deployment is demo with web and notes; optional integrations are disabled. New accounts have
provider quotas and resource charges: inspect plans and review them before applying infrastructure.

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
m doctor -- --stage local
direnv allow
az login
az account set --subscription 00000000-0000-0000-0000-000000000000
```

`infrastructure/cli/provider/envrc` sets the region, subscription and tenant, and points Terraform's
`ARM_*` variables at the same values; `az` must be on `PATH` (`PROVIDER_REQUIRED_PACKAGES` warns if it
is not). You also need Docker with `buildx`, because images build locally and push straight to the
container registry.

## 5. Operations configuration

```
m terraform-plan-operations
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

## 6. Essential services and secrets

Follow the Clerk JWT-template and organization recipe in `docs/getting-started.md`. Configure the public
feature keys and JWKS URL in project.json, then apply configuration. Create or select a Vercel team,
record its id in project.json, and obtain its Terraform token. Store secret values in the cloud console;
do not put them in project.json or the conversation.

Create `CLERK-SECRET-KEY` and `GEMINI-API-KEY` in the feature vault, and `VERCEL-TERRAFORM-API-KEY`
in the operations vault. Services create their own Redis secret. Before production, create the production
Clerk instance's secret key and Gemini key in the production vault.

Only when enabled, create `LOGFIRE-WRITE-TOKEN` in each deployment vault and `SENTRY-DSN` in operations.
Admin's Entra configuration and ingress allowlist are only needed when enabling admin. Preserve the ACR
login helper's all-zero token username; it is a protocol constant, not a subscription placeholder.

The sample has no Clerk webhook handler, so a webhook signing secret is not required. Add webhook
configuration alongside a feature that actually consumes it.

## 7. Demo

After operations exists, copy its returned identifiers into project.json and apply configuration again.
Delegate the DNS zone before requesting certificates. Diagnostic cloud checks may report missing outputs
until that provisioning step is complete; never invent provider-assigned project numbers or object ids.

```sh
m doctor -- --stage cloud
FEATURE_ENVIRONMENT=demo m terraform-plan-services
FEATURE_ENVIRONMENT=demo m create-feature-environment
m doctor -- --stage demo
```

Terraform validates the complete configuration and permissions; doctor checks prerequisites and read-only
access, not every cloud permission. Deploy only after requesting/reviewing the infrastructure changes.
The create command deploys configured surfaces, stops on failed commands, and limits health polling to ten
minutes. Complete the signed-in note walkthrough and record actual results in `docs/setup-verification.md`.

## 8. CI and production

Set repository variables `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, and `AZURE_SUBSCRIPTION_ID` from the
operations Terraform identity. Federation subjects must match your exact repository and main branch.
No Azure client secret is needed. Install the containerapp CLI extension manually before deployment;
shell activation no longer installs it implicitly.

`GEMINI_API_KEY` is needed by integration tests that call the model. `EXPO_TOKEN` is only needed for enabled
mobile distribution. Keep all secret values out of the repository.

PR merges into main deploy configured surfaces to demo. They do **not** deploy production. Production uses
an explicit Deployment workflow dispatch: configure the production Clerk publishable key/JWKS URL, create
production secrets and DNS, and review the requested surfaces before dispatching. The demo environment
must exist before its first automated update. Operations changes are a separate explicit workflow input.

## 9. Optional surfaces and cleanup

Enable admin, MCP, mobile, Sentry, or Logfire in project.json when needed, supply their credentials, then
run configure-project and deployment for the enabled surfaces. MCP also needs Clerk OAuth configuration;
mobile needs Expo/EAS and the appropriate store accounts. Keep monitoring disabled until its secrets exist.

Use `FEATURE_ENVIRONMENT=demo m destroy-feature-environment` only when ready to delete demo's data and
resources. If removing an optional surface, destroy it before disabling it in project.json so its state
remains selected for cleanup. Shared operations resources, DNS delegation, and manually created state
storage are not removed by feature cleanup. Review the operations destroy plan separately, preserve any
state needed for recovery, and remove the state bucket/container last through the cloud console.

Fresh-account deployment and cleanup on this cloud are unverified until a dated walkthrough is recorded.
