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
   bootstrap, then remove it. The grant takes a minute or two to propagate; `gcloud auth
   print-access-token --impersonate-service-account=<email>` tells you when it has.
6. Enable these APIs on the operations project: artifactregistry, cloudbilling, cloudbuild,
   cloudresourcemanager, compute, domains, dns, iam, iamcredentials, identitytoolkit,
   pubsub, secretmanager, servicenetworking, storage (all `.googleapis.com`).
7. Fill `infrastructure/terraform/configurations/operations/terraform.tfvars` with the
   organization id, folder id, billing account id, operations project id and number.
8. Put a real engineer account in `infrastructure/terraform/modules/permissions/main.tf`. IAM
   rejects members that do not exist, which fails the first apply half way through.

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
that to the new repository first. If a configuration was ever initialised with `-backend=false`
(the validation gate does that), delete its `.terraform` directory before the first real apply.

The apply prints the new project ids and numbers. Copy them into `infrastructure/cli/Makefile`,
`.envrc`, and `library/library/infrastructure/cloud/constants.py`.

## 5. Images the cache VM pulls

The Redis VM pulls `redis-stack-server` and `redis_exporter` from the operations project's
`public-images` registry rather than Docker Hub. After `m terraform-operations` created that
registry, push both once, using the versions in
`infrastructure/terraform/modules/compute-engine-redis/variables.tf`:

```
gcloud auth configure-docker us-central1-docker.pkg.dev
docker pull --platform linux/amd64 redis/redis-stack-server:7.4.0-v3
docker tag redis/redis-stack-server:7.4.0-v3 us-central1-docker.pkg.dev/<operations-project-id>/public-images/redis-stack-server:7.4.0-v3
docker push us-central1-docker.pkg.dev/<operations-project-id>/public-images/redis-stack-server:7.4.0-v3
docker pull --platform linux/amd64 oliver006/redis_exporter:v1.67.0
docker tag oliver006/redis_exporter:v1.67.0 us-central1-docker.pkg.dev/<operations-project-id>/public-images/redis_exporter:v1.67.0
docker push us-central1-docker.pkg.dev/<operations-project-id>/public-images/redis_exporter:v1.67.0
```

If the VM came up before the images existed, `gcloud compute instances reset` it so the startup
script runs again.

## 6. Secrets, by hand

Terraform reads these from Secret Manager and never creates them. Secret Manager refuses an empty
payload, so every one needs a real value. Create each one in both the production and feature
projects:

| Secret | Used by |
| --- | --- |
| `CLERK_SECRET_KEY` | services, admin, web |
| `CLERK_WEBHOOK_SECRET` | services |
| `GEMINI_API_KEY` | services |
| `SENTRY_DSN` | services, admin |
| `LOGFIRE_WRITE_TOKEN` | services, admin |

Admin sits behind Identity-Aware Proxy with its own OAuth client, which the IAP admin API can no
longer create. In each project open Google Auth Platform in the console, configure an internal
consent screen, create a Web application client, and store its id and secret as
`ADMIN_IAP_OAUTH_CLIENT_ID` and `ADMIN_IAP_OAUTH_CLIENT_SECRET`.

And this one in the operations project:

| Secret | Used by |
| --- | --- |
| `VERCEL_TERRAFORM_API_KEY` | web terraform |

## 7. Clerk

Create a Clerk application with organizations enabled and two instances: development (feature
environments) and production. Put the publishable keys in
`infrastructure/terraform/modules/environment/{feature,production}.tf`, the secret keys in Secret
Manager as above, and the production instance's DNS records in `operations/dns.tf` once you have
them. The webhook secret comes from a Clerk webhook pointed at the services API.

## 8. Vercel

Create or pick a team, put its id in `configurations/web/terraform.tfvars`, and store a team
token as `VERCEL_TERRAFORM_API_KEY`. Terraform creates the project.

## 9. Feature environment

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

Or `m create-feature-environment`, which runs the same sequence. The first services apply in a
new project usually fails once on Eventarc triggers while the Eventarc service agent's
permissions propagate; run it again.

## 10. GitHub

Repository secrets: `CLERK_SECRET_KEY`, `GEMINI_API_KEY`, `EXPO_TOKEN`.

Repository variables: `TERRAFORM_SERVICE_ACCOUNT` (the `terraform` service account email) and
`TERRAFORM_WORKLOAD_IDENTITY_PROVIDER`, which is
`projects/<operations-project-number>/locations/global/workloadIdentityPools/terraform/providers/terraform`.

`pull-request-checks` runs on every PR. `create-feature-environment` and
`destroy-feature-environment` are manual triggers. The `deployment` workflow runs when a PR into
`main` is merged: it applies the operations terraform, deploys to a long-lived feature environment
named `demo`, then applies and deploys production. It can also be dispatched by hand per surface.

## 11. Production

Merge to `main`. The `deployment` workflow does the rest. The first run needs the `demo` feature
environment to exist, so create it once from a branch named `demo` with
`m create-feature-environment`.
