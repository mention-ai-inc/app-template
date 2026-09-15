# Bootstrap

How a fresh copy of this scaffold becomes a deployed product on AWS. Every id below is a placeholder
until you finish `docs/rename.md`; do that first.

Feature environments are **name-prefixed resources in one account**, not accounts of their own. There
is one AWS account, one VPC, one ECS cluster, and one Route 53 hosted zone; `production` is the
`default` Terraform workspace and every feature environment is a workspace whose name becomes the
prefix on everything it creates.

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
direnv allow
m init
aws configure sso
aws sso login
```

`infrastructure/cli/provider/envrc` sets `AWS_REGION` and `AWS_PROFILE`; `aws` must be on `PATH`
(`PROVIDER_REQUIRED_PACKAGES` warns if it is not). You also need Docker with `buildx`, because images
build locally and push straight to ECR.

## 5. Operations configuration

```
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

## 6. Secrets, by hand

Terraform reads these from Secrets Manager and never creates them. Create each one once in the account,
with a real value — a secret with no version fails the data source at plan time.

| Secret | Used by |
| --- | --- |
| `CLERK_SECRET_KEY` | services, admin, mcp, web |
| `CLERK_WEBHOOK_SECRET` | services, admin |
| `GEMINI_API_KEY` | services, admin |
| `LOGFIRE_WRITE_TOKEN` | services, admin |
| `SENTRY_DSN` | services, admin |
| `VERCEL_TERRAFORM_API_KEY` | web terraform |
| `ADMIN_OIDC_CLIENT_ID` | admin load balancer |
| `ADMIN_OIDC_CLIENT_SECRET` | admin load balancer |

`REDIS_PASSWORD` is created by the operations configuration; do not create it by hand.

The admin API sits behind the load balancer's own OIDC authentication rather than an identity-aware
proxy. Register a confidential OAuth client with the identity provider named in
`configurations/admin/terraform.tfvars` (the placeholders point at Clerk), allow
`https://admin.<domain>/oauth2/idpresponse` as its redirect URI, and store its id and secret as the two
`ADMIN_OIDC_*` secrets above.

## 7. Clerk

Create a Clerk application with organizations enabled and two instances: development (feature
environments) and production. Put the publishable keys in
`infrastructure/terraform/modules/environment/{feature,production}.tf`, the secret key in Secrets
Manager as above, and the production instance's DNS records in `operations/dns.tf` once you have them.
The webhook secret comes from a Clerk webhook pointed at the services API.

## 8. Vercel

Create or pick a team, put its id in `configurations/web/terraform.tfvars`, and store a team token as
`VERCEL_TERRAFORM_API_KEY`. Terraform creates the project and the deployment.

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
`https://<environment>api.<domain>/health`.

Two things about the first apply in a new workspace:

- Every ECS service and job comes up on a placeholder `busybox` image. It is the deploy that points it
  at a real one, so a service that is stuck restarting before you have deployed is expected.
- Certificate validation adds a Route 53 record and then waits for ACM. If the hosted zone is not yet
  delegated (step 3) this is where the apply hangs.

## 10. GitHub

Repository variables:

- `TERRAFORM_ROLE_ARN` — `arn:aws:iam::000000000000:role/terraform`
- `AWS_REGION` — the deployment region

Repository secrets: `CLERK_SECRET_KEY`, `GEMINI_API_KEY`, `EXPO_TOKEN`.

There are **no AWS access keys**. Every workflow authenticates with `aws-actions/configure-aws-credentials`
against the GitHub OIDC provider created in the operations configuration, whose trust policy pins both
the audience and `github_repo`. Set `github_repo` in the tfvars to the real repository before that apply,
or CI cannot assume anything.

`pull-request-checks` and `pull-request-cloud-checks` run on every PR. `create-feature-environment` and
`destroy-feature-environment` are manual triggers. The `deployment` workflow runs when a PR into `main`
is merged: it deploys to a long-lived feature environment named `demo`, and it can also be dispatched by
hand per surface to ship production.

## 11. Production

Merge to `main`. The `deployment` workflow does the rest. The first run needs the `demo` feature
environment to exist, so create it once from a branch named `demo` with `m create-feature-environment`.
