# Rename: AWS ids

Section 2 of `docs/rename.md` on this branch. Work through it there, then come back.

AWS puts everything in **one account**, so there is a single id to replace rather than three, and it
is not secret but it is not public either. What varies per environment is a Terraform workspace
prefix, not an account. The one name that must be globally unique is the state bucket's.

Placeholders: account id `000000000000`, bucket prefix `acme-operations-0000`, cluster `acme`,
region `us-east-1`.

```
git grep -n -E "0{12}|acme-operations-0000"
```

| File | What |
| --- | --- |
| `infrastructure/cli/provider/targets.mk` | the three exported account ids (all the same account here), the bucket prefix, the cluster name, the region |
| `infrastructure/cli/provider/feature-environment` | the account id fallbacks, which build `ECR_REGISTRY` |
| `infrastructure/terraform/configurations/{operations,services,admin,mcp,web}/base.tf` | the `terraform` role ARN and the state bucket |
| `infrastructure/terraform/configurations/operations/terraform.tfvars` | `account_id`, `bucket_name_prefix`, and the VPC CIDR blocks if `10.0.0.0/16` clashes with something you already run |
| `infrastructure/terraform/configurations/admin/terraform.tfvars` | the four `oidc_*` endpoints, which are your identity provider's, not a placeholder domain |
| `.agents/skills/investigate-systems/references/aws-access.md` | the account id in the worked examples |
| `library/library/presentation/auth/direct.py` | the `JWK_DOMAINS_BY_DEPLOYMENT` **keys**, which are account ids here |

The account id is not a secret, but it is an identifier an attacker can use, so keep it out of
anything public. `bucket_name_prefix` must be globally unique across all of S3 — a name someone else
has taken fails at apply with a confusing permissions error rather than a naming one.
