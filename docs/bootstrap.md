# Bootstrap on GCP

Start with `docs/getting-started.md`. Generate a product repository and configure its identity before
following this guide. The selected cloud is already on your product's main branch. Keep project.json
as the nonsecret setup input and use configure-project after each group of new identifiers.

The foundation steps below are manual account setup. They are not performed by new-project or doctor.
A first deployment is demo with web and notes; optional integrations are disabled. New accounts have
provider quotas and resource charges: inspect plans and review them before applying infrastructure.

## 1. Google Cloud, by hand

Run `m inspect-cloud-account` to list the configured account, accessible organizations, and open
billing accounts before choosing the product's foundation. This command is read-only and prints no tokens.

With foundation inputs set in project.json, `m bootstrap-cloud-foundation` previews the target.
After explicitly approving cloud creation and the IAM grants below, run
`m bootstrap-cloud-foundation -- --apply`. It records assigned folder and operations-project numbers
and resumes existing resources in the selected folder. It enables bucket versioning without installing
a deletion lifecycle policy; review a seven-version cleanup policy separately before enabling it.

Terraform cannot create the project that holds its own state, so these steps are manual. They
mirror `infrastructure/terraform/configurations/operations/README.md`.

1. Create a folder under the organization for this product.
2. Create the operations project inside it. Its id becomes `OPERATIONS_PROJECT_ID` in
   `infrastructure/cli/provider/targets.mk` and `operations_project_id` in every `terraform.tfvars`.
3. Create a Cloud Storage bucket named `<operations-project-id>--terraform-state` with object
   versioning set to keep 7 versions.
4. Create a service account named `terraform` in the operations project and grant it:
   - Folder level: Folder Admin, Project Creator, Project Deleter, Project IAM Admin,
     Compute Shared VPC Admin.
   - Operations project level: Owner.
   - Billing account: Billing Account Administrator.
   - On itself: Service Account Token Creator.
5. Grant yourself Service Account Token Creator on that service account and keep it for as long
   as you create feature environments or apply Terraform locally: `m create-feature-environment`
   and `m terraform-*` impersonate it. Production ships through GitHub Actions with workload
   identity and does not need it. The grant takes a minute or two to propagate; `gcloud auth
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
Use `m inspect-cloud-dns` to read the zone's assigned name servers.

## 3. Local setup

```
m doctor -- --stage local
direnv allow
gcloud auth login
gcloud auth application-default login
```

## 4. Operations project

```
m terraform-plan-operations
m terraform-operations
```

This creates the production and feature projects, networking, the artifact registry, the
`REDIS_PASSWORD` secret, the feature Firestore database, workload identity pools for GitHub
Actions, and the DNS zone. The workload identity pools bind to `github_repo` in the tfvars, so set
that to the new repository first. If a configuration was ever initialised with `-backend=false`
(the validation gate does that), delete its `.terraform` directory before the first real apply.

The apply prints the new project ids and numbers. Enter them in `project.json`, then run `m configure-project -- --apply` and
`m update-local-dependencies`: the admin and service virtualenvs vendor a copy of the library and
keep the old constants until they are reinstalled.
`m operations-outputs` reads these nonsecret outputs again after the apply; `m inspect-cloud-projects`
checks the projects currently present in the configured folder.

## 5. Images the cache VM pulls

Cache image versions, Linux architecture, and pinned digests live in
`infrastructure/terraform/modules/compute-engine-redis/cache-images.json`. Terraform defaults and
the publication command both read this manifest. Update it and verify the source digest together.

The Redis VM pulls `redis-stack-server` and `redis_exporter` from the operations project's
`public-images` registry rather than Docker Hub. After `m terraform-operations` created that
registry, inspect both images and confirm Docker is running:

```sh
m inspect-cache-image-sources
m inspect-container-engine
```

After the user requests image publication, run `m publish-cache-images`. It publishes the verified
Linux amd64 digests for `redis-stack-server:7.4.0-v3` and `redis_exporter:v1.67.0` to the configured
operations registry. It uses a separate temporary Docker configuration with the GCP credential helper;
no secret values are written into the repository. Reverify and update the pinned digests if changing
the image manifest.

Publish the images before creating the cache VM so its startup script can pull them successfully.

## 6. Essential services and secrets

Follow the Clerk JWT-template and organization recipe in `docs/getting-started.md`. Configure the public
feature keys and JWKS URL in project.json, then apply configuration. Create or select a Vercel team,
record its id in project.json, and obtain its Terraform token. Store secret values in the cloud console;
do not put them in project.json or the conversation.

After storing the feature `CLERK_SECRET_KEY`, run `m inspect-clerk`. This read-only check uses the
secret in memory to verify the instance and JWT template, and checks public organization and sign-in
settings. It prints no secret values. The signed-in walkthrough is still required after deployment.

Create `CLERK_SECRET_KEY` and `GEMINI_API_KEY` with real values in the feature project. Create
`VERCEL_TERRAFORM_API_KEY` in the operations project. `REDIS_PASSWORD` is created by operations.
For production, use that Clerk instance's secret key in the production project and provide its Gemini key.

After storing the Vercel token, run `m inspect-vercel`. This read-only check uses the secret in memory
to verify access to the configured team. It prints no secret values and creates no Vercel resources.

When enabled, Logfire uses `LOGFIRE_WRITE_TOKEN` in the deployment project and Sentry uses `SENTRY_DSN`
in operations. Admin additionally needs its IAP OAuth client id and secret; follow the admin configuration
only when enabling that surface. Neither is required for the initial web deployment.

The sample has no Clerk webhook handler, so a webhook signing secret is not required. Add webhook
configuration alongside a feature that actually consumes it.

## 7. Demo

After operations exists, copy its returned identifiers into project.json and apply configuration again.
Delegate the DNS zone before requesting certificates. Diagnostic cloud checks may report missing outputs
until that provisioning step is complete; never invent provider-assigned project numbers or object ids.

Use `m inspect-demo-prerequisites` to read public DNS delegation and list the operations registry's
cached images without publishing images or changing DNS.

After deployment, `m verify-demo-endpoints` checks API health, published notes routes, unauthenticated
request rejection, and web reachability. Use `m inspect-demo-build` for the latest feature build status
and `m inspect-demo-serving` for Cloud Run readiness and public TLS/DNS diagnostics. These read-only
checks do not replace the signed-in note and summary walkthrough.

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

Set repository variables `TERRAFORM_SERVICE_ACCOUNT` and `TERRAFORM_WORKLOAD_IDENTITY_PROVIDER`
from the operations identity configuration. The federation must trust your exact repository. No cloud
service-account key belongs in GitHub secrets.

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

## Summary diagnostics and recovery

`m inspect-project-routing` compares configured project identifiers with generated runtime constants.
Cloud and demo doctor additionally compare project numbers with Google Cloud. Fix a mismatch with
assigned outputs and `m configure-project -- --apply`, then refresh local dependencies.

`m inspect-demo-summary-errors` reports worker timestamps, service names, severity, and HTTP status;
it omits payloads and note content. `m inspect-demo-summary-queue` reports delivery metadata.
`m demo-note -- --organization-id <id> --note-id <id>` reports stored status, summary presence,
and command processing metadata. It defaults to demo; `--environment <feature>` selects another
feature environment and rejects production. After fixing the cause and obtaining a request for
recovery, add `--retry` to redispatch exactly one eligible command through its existing trigger.
The operation rechecks state transactionally and never writes a summary directly.

## Deployment controls and verification

Automatic demo deployment on merge defaults to enabled. Set `deployment.auto_demo` to false to
pause it before cloud authentication. An explicitly requested manual Deployment workflow run with
`environment=demo` remains available; omitted environment inputs retain production behavior.
Partial demo runs do not advance the complete demo deployment baseline.

Update the compact setup checkpoint after the real sign-in, organization, note, summary, and reload
walkthrough. For enabled Sentry and Logfire, verify an actual event and trace in their consoles;
doctor's secret checks do not establish delivery. Do not copy logs, tokens, note text, or a setup diary
into the checkpoint.
