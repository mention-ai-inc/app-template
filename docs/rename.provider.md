# Rename: GCP ids

Section 2 of `docs/rename.md` on this branch. Work through it there, then come back.

GCP addresses everything by **project**, and IAP addresses some things by **project number**, which
is a different value you cannot derive from the id. The scaffold ships three projects.

Placeholders: `acme-operations-0000`, `acme-production-0000`, `acme-feature-0000`; project numbers
`000000000001` to `000000000003`; organization id, folder id and project number `000000000000`;
billing account `000000-000000-000000`.

```
git grep -n -E "acme-(operations|production|feature)-0000|0{12}|000000-000000-000000"
```

| File | What |
| --- | --- |
| `infrastructure/cli/provider/targets.mk` | the three exported project ids |
| `infrastructure/cli/provider/envrc` | `GOOGLE_CLOUD_PROJECT` (the feature project) |
| `infrastructure/cli/provider/helpers/get-feature-instance-ip` | the feature project |
| `library/providers/gcp/library_provider_gcp/cloud/constants.py` | the three ids **and their numbers** |
| `infrastructure/terraform/configurations/operations/terraform.tfvars` | org, folder, billing, operations id and number |
| `infrastructure/terraform/configurations/{operations,services,admin,mcp,web}/base.tf` | state bucket and the `terraform` service account email |
| `infrastructure/terraform/configurations/{services,admin,mcp,web}/terraform.tfvars` | `operations_project_id` |
| `infrastructure/terraform/configurations/admin/{admin,iap}.tf` | admin project references |
| `library/library/presentation/auth/direct.py` | the `JWK_DOMAINS_BY_DEPLOYMENT` **keys**, which are project ids here |

Project numbers are the one value you cannot invent: read them back with
`gcloud projects describe <id> --format='value(projectNumber)'` once the projects exist, which is
part of `docs/bootstrap.md` rather than this step.
