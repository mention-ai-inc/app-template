# Bootstrap on AWS

Start with `docs/getting-started.md`. Generate a product repository and configure its identity before
following this guide. The selected cloud is already on your product's main branch. Keep project.json
as the nonsecret setup input and use configure-project after each group of new identifiers.

The foundation steps below are manual account setup. They are not performed by new-project or doctor.
A first deployment is demo with web and notes; optional integrations are disabled. New accounts have
provider quotas and resource charges: inspect plans and review them before applying infrastructure.

## 1. AWS, by hand

Terraform cannot create the account it runs in, the bucket it keeps its state in, or the role it
assumes to do either. Those come first, manually, exactly once. They mirror
`infrastructure/terraform/configurations/operations/README.md`.

1. Create the AWS account, or pick the existing one. Note its id: it replaces `000000000000`
   throughout the Terraform and in `infrastructure/cli/provider/targets.mk`.
2. Create an S3 bucket named `acme-operations-0000--terraform-state` in `us-east-1`, with versioning
   on and public access blocked. State locking uses the bucket's own lock files (`use_lockfile`), so
   there is no DynamoDB lock table to create. The name is `bucket_name_prefix` plus `--terraform-state`
   and is repeated in every configuration's `base.tf`.
3. Create an IAM role named `terraform` with `AdministratorAccess`, trusted by the account root so an
   engineer can assume it. Terraform takes the role over on the first apply, including the GitHub
   trust policy that lets CI assume it, so the hand-made version only has to survive one apply.
4. Put a real engineer account in `infrastructure/terraform/modules/permissions/main.tf`. IAM rejects
   members that do not exist, which fails the first apply half way through.
5. Fill `infrastructure/terraform/configurations/operations/terraform.tfvars` with the account id,
   the bucket name prefix, the GitHub repository, the region, and the domain.

## 2. Service quotas

Raise these before the first real deploy, not after it fails:

- **Fargate On-Demand vCPU** in the deployment region. The default is small enough that one feature
  environment plus production exhausts it.
- **Rules per Application Load Balancer listener**, if you expect more than a handful of services:
  the API load balancer routes one rule per service.
- **VPCs per region**, if the account already holds others.

## 3. Domain

`operations/dns.tf` creates the hosted zone for `domain_name`. After the first `m terraform-operations`,
point the registrar's NS records at the zone's name servers (or add an NS record in the parent zone if
you are delegating a subdomain). Do this **before** anything asks for a certificate: ACM validates by
DNS and `aws_acm_certificate_validation` will wait forever otherwise.

## 4. Local setup

```
m doctor -- --stage local
direnv allow
aws configure sso
aws sso login
```

`infrastructure/cli/provider/envrc` sets `AWS_REGION` and `AWS_PROFILE`; `aws` must be on `PATH`
(`PROVIDER_REQUIRED_PACKAGES` warns if it is not). You also need Docker with `buildx`, because images
build locally and push straight to ECR.

## 5. Operations configuration

```
m terraform-plan-operations
m terraform-operations
```

This creates the VPC and its subnets, the ECS cluster, the hosted zone, the shared `docker-cache` and
`public-images` ECR repositories, the static-asset and load-balancer-log buckets, the `REDIS_PASSWORD`
secret, the GitHub OIDC provider, and the `github-actions` and `terraform` roles. Operations always
applies in the `default` workspace; the target does not take a feature environment.

The apply prints the account id, the VPC id, the subnet ids, and both role ARNs. Nothing downstream
needs copying by hand — the other configurations read them through `terraform_remote_state`.

If a configuration was ever initialised with `-backend=false`, delete its `.terraform` directory before
the first real apply.

## 6. Essential services and secrets

Follow the Clerk JWT-template and organization recipe in `docs/getting-started.md`. Configure the public
feature keys and JWKS URL in project.json, then apply configuration. Create or select a Vercel team,
record its id in project.json, and obtain its Terraform token. Store secret values in the cloud console;
do not put them in project.json or the conversation.

Create `feature/CLERK_SECRET_KEY`, `GEMINI_API_KEY`, and `VERCEL_TERRAFORM_API_KEY` in Secrets Manager.
`REDIS_PASSWORD` is created by operations. Before production, create `production/CLERK_SECRET_KEY` from
the production Clerk instance. The two Clerk secret names are distinct even though the account is shared.

Only when enabled, create `LOGFIRE_WRITE_TOKEN` for Logfire and `SENTRY_DSN` for Sentry. Admin additionally
requires `ADMIN_OIDC_CLIENT_ID` and `ADMIN_OIDC_CLIENT_SECRET`, with its configured identity-provider
endpoints and `https://admin.<domain>/oauth2/idpresponse` callback. Admin is not part of first deployment.

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

Set repository variables `TERRAFORM_ROLE_ARN` and `AWS_REGION`. Use the role ARN from your operations
configuration and ensure its GitHub OIDC trust names the exact repository. No AWS access keys are required.

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
