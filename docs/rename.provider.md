# Rename: Azure ids

Section 2 of `docs/rename.md` on this branch. Work through it there, then come back.

Azure needs two GUIDs — the **subscription** everything is billed to and the **tenant** that
authenticates you — and three **resource groups**. The container registry is the awkward one: ACR
names allow only letters and digits, so it cannot carry the hyphens the resource groups use.

Placeholders: subscription and tenant `00000000-0000-0000-0000-000000000000`; resource groups
`acme-operations-0000`, `acme-production-0000`, `acme-feature-0000`; registry `acmeoperations0000`;
region `eastus`.

```
git grep -n -E "00000000-0000-0000-0000-0{12}|acme-?(operations|production|feature)-?0000"
```

| File | What |
| --- | --- |
| `infrastructure/cli/provider/targets.mk` | subscription, tenant, the three resource groups, the registry name, the region |
| `infrastructure/cli/provider/envrc` | subscription and tenant |
| `infrastructure/cli/provider/feature-environment` | the resource group each environment maps to |
| `infrastructure/terraform/configurations/{operations,services,admin,mcp,web}/base.tf` | subscription and tenant in the provider and backend blocks — **the backend block too**, which is easy to miss because it is not interpolated |
| `infrastructure/terraform/configurations/{operations,services,admin,mcp}/terraform.tfvars` | `subscription_id`, `tenant_id`, `operations_resource_group_name` |
| `.agents/skills/deploy-branch/SKILL.md`, `.agents/skills/investigate-systems/references/azure-access.md` | the ids in the worked examples |
| `library/library/presentation/auth/direct.py` | the `JWK_DOMAINS_BY_DEPLOYMENT` **keys**, which are subscription ids here |

**Leave one all-zeros GUID alone.** `infrastructure/cli/provider/helpers/acr-login` sets
`TOKEN_LOGIN_USERNAME=00000000-0000-0000-0000-000000000000`, which is the username ACR requires when
signing in with an access token rather than a password. It is not a placeholder, and a global
find-and-replace across the repository will break every image push with an authentication error that
does not mention the username.
