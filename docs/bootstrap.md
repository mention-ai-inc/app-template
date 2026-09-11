# Bootstrap

How a fresh copy of this scaffold becomes a deployed product. Every id below is a placeholder until
you finish `docs/rename.md`; do that first.

## 1. Google Cloud, by hand

Terraform cannot create the project that holds its own state, so these steps are manual. They
mirror `infrastructure/terraform/configurations/operations/README.md`.

1. Create a folder under the organization for this product.
2. Create the operations project inside it. Its id becomes `OPERATIONS_PROJECT_ID` in
   `infrastructure/cli/Makefile` and `operations_project_id` in every `terraform.tfvars`.
3. Create a Cloud Storage bucket named `<operations-project-id>--terraform-state` with object
   versioning set to keep 7 versions.
4. Create a service account named `terraform` in the operations project and grant it:
   - Folder level: Folder Admin, Project Creator, Project Deleter, Project IAM Admin,
     Compute Shared VPC Admin.
   - Operations project level: Owner.
   - Billing account: Billing Account Administrator.
   - On itself: Service Account Token Creator.
5. Grant yourself Service Account Token Creator on that service account for the duration of the
   bootstrap, then remove it.
6. Enable these APIs on the operations project: artifactregistry, cloudbilling,
   cloudresourcemanager, compute, domains, dns, iam, iamcredentials, identitytoolkit,
   secretmanager, servicenetworking (all `.googleapis.com`).
7. Fill `infrastructure/terraform/configurations/operations/terraform.tfvars` with the
   organization id, folder id, billing account id, operations project id and number.

## 2. Domain

`operations/dns.tf` creates a managed zone for `domain_name`. After the first
`m terraform-operations`, point the domain's NS records at the zone's name servers (at the
registrar, or as an NS record in the parent zone if you delegate a subdomain).

## 3. Local setup

```
direnv allow
m init
gcloud auth login
gcloud auth application-default login
```

## 4. Operations project

```
m terraform-operations
```

This creates the production and feature projects, networking, the artifact registry, the
`REDIS_PASSWORD` secret, the feature Firestore database, workload identity pools for GitHub
Actions, and the DNS zone. The workload identity pools bind to `github_repo` in the tfvars, so set
that to the new repository first.

## 5. Secrets, by hand

Terraform reads these from Secret Manager and never creates them. Create each one in both the
production and feature projects:

| Secret | Used by |
| --- | --- |
| `CLERK_SECRET_KEY` | services, admin, web |
| `CLERK_WEBHOOK_SECRET` | services |
| `GEMINI_API_KEY` | services |
| `SENTRY_DSN` | services, admin |
| `LOGFIRE_WRITE_TOKEN` | services, admin |

And this one in the operations project:

| Secret | Used by |
| --- | --- |
| `VERCEL_TERRAFORM_API_KEY` | web terraform |

## 6. Clerk

Create a Clerk application with organizations enabled and two instances: development (feature
environments) and production. Put the publishable keys in
`infrastructure/terraform/modules/environment/{feature,production}.tf`, the secret keys in Secret
Manager as above, and the production instance's DNS records in `operations/dns.tf` once you have
them. The webhook secret comes from a Clerk webhook pointed at the services API.

## 7. Vercel

Create or pick a team, put its id in `configurations/web/terraform.tfvars`, and store a team
token as `VERCEL_TERRAFORM_API_KEY`. Terraform creates the project.

## 8. Feature environment

From a branch (the branch name becomes the workspace and the `FEATURE_ENVIRONMENT` prefix):

```
m terraform-services
m terraform-mcp
m terraform-admin
m deploy-notes
m deploy-admin
m deploy-mcp
m deploy-web
```

Or `m create-feature-environment`, which runs the same sequence.

## 9. GitHub

Repository secrets: `CLERK_SECRET_KEY`, `GEMINI_API_KEY`, `EXPO_TOKEN`.

Repository variables: `TERRAFORM_SERVICE_ACCOUNT` (the `terraform` service account email) and
`TERRAFORM_WORKLOAD_IDENTITY_PROVIDER`, which is
`projects/<operations-project-number>/locations/global/workloadIdentityPools/terraform/providers/terraform`.

`pull-request-checks` runs on every PR. `create-feature-environment` and
`destroy-feature-environment` are manual triggers. The `deployment` workflow runs on every push to
`main`: it applies the operations terraform, deploys to a long-lived feature environment named
`demo`, then applies and deploys production.

## 10. Production

Merge to `main`. The `deployment` workflow does the rest. The first run needs the `demo` feature
environment to exist, so create it once from a branch named `demo` with
`m create-feature-environment`.
