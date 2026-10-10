# Operations

Everything in this configuration is shared by every environment, so it is always applied in the
`default` workspace and never in a feature workspace: the account's VPC, the ECS cluster, the hosted
zone, the shared ECR repositories, the state bucket's siblings, and the roles CI assumes.

## Before the first apply

Terraform cannot create the account it runs in, the bucket it keeps its state in, or the role it
assumes to do either. Those three come first, by hand, exactly once.

1. Create the AWS account, or pick the existing one. Every environment lives in it; feature
   environments are name-prefixed resources, not accounts.
1. Create an S3 bucket named `[account-id]--terraform-state` in `us-east-1`, with versioning on and
   public access blocked. State locking uses the bucket's own lock files, so there is no DynamoDB
   table to create.
1. Create an IAM role named `terraform` with `AdministratorAccess`, trusted by the account root so
   that an engineer can assume it, and note its ARN. Terraform takes the role over on the first
   apply, including the GitHub trust policy that lets CI assume it.
1. Register the domain, or delegate it. `terraform apply` creates the hosted zone; point the
   registrar at the name servers it outputs before anything asks for a certificate, because ACM
   validates by DNS and will wait forever otherwise.
1. Create the secrets the other configurations read: `CLERK_SECRET_KEY`, `CLERK_WEBHOOK_SECRET`,
   `GEMINI_API_KEY`, `LOGFIRE_WRITE_TOKEN`, `SENTRY_DSN`, `VERCEL_TERRAFORM_API_KEY`,
   `ADMIN_OIDC_CLIENT_ID`, and `ADMIN_OIDC_CLIENT_SECRET`. `REDIS_PASSWORD` is created here.

## Service quotas worth raising first

The defaults that bite a fresh account are the Fargate on-demand vCPU quota, the number of rules per
application load balancer listener, and the number of VPCs per region. Raise the first before the
first real deploy.
