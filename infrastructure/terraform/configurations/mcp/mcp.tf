locals {
  api_url = "https://${local.feature_environment}${var.api_subdomain}.${var.domain_name}"
}

data "aws_secretsmanager_secret" "clerk-secret-key" {
  name = "CLERK_SECRET_KEY"
}

module "task-execution-role" {
  source = "../../modules/iam-task-role"

  role_name   = "${local.feature_environment}mcp-execution"
  policy_arns = ["arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"]
  actions     = ["secretsmanager:GetSecretValue", "kms:Decrypt"]
}

module "mcp-task-role" {
  source = "../../modules/iam-task-role"

  role_name = "${local.feature_environment}mcpclient-s"
  actions = [
    "cloudwatch:PutMetricData",
    "logs:CreateLogStream",
    "logs:PutLogEvents",
    "secretsmanager:GetSecretValue",
  ]
}

module "mcp-server" {
  source = "../../modules/ecs-server"

  region              = var.preferred_region
  feature_environment = local.feature_environment
  cluster_arn         = local.cluster_arn
  cluster_name        = local.cluster_name
  service_name        = "mcp"
  server_name         = "rest"

  task_role_arn      = module.mcp-task-role.arn
  execution_role_arn = module.task-execution-role.arn

  cpu                       = "512"
  memory                    = "1024"
  container_concurrency     = 80
  timeout_seconds           = 300
  minimum_instances         = local.is_production ? 2 : 1
  maximum_instances         = 10
  health_check_request_path = "/health"
  log_retention_days        = var.log_retention_days

  vpc_id                          = local.vpc_id
  subnet_ids                      = local.private_subnet_ids
  load_balancer_security_group_id = module.mcp-load-balancer.security_group_id

  env = {
    API_URL               = local.api_url
    CLERK_PUBLISHABLE_KEY = module.environment.settings.tokens.clerk_publishable_key
  }

  secrets = {
    CLERK_SECRET_KEY = data.aws_secretsmanager_secret.clerk-secret-key.arn
  }
}

module "mcp-load-balancer" {
  source = "../../modules/application-load-balancer"

  feature_environment = local.feature_environment
  surface_name        = "mcp"
  domain_name         = "${var.mcp_subdomain}.${var.domain_name}"
  hosted_zone_id      = local.hosted_zone_id

  vpc_id     = local.vpc_id
  subnet_ids = local.public_subnet_ids

  default_target_group_arn    = module.mcp-server.target_group_arn
  deletion_protection_enabled = local.is_production
  access_log_bucket           = data.terraform_remote_state.operations.outputs.load_balancer_logs_bucket_name
}

output "mcp_fqdn" {
  description = "Hostname the MCP server is served on."
  value       = module.mcp-load-balancer.fqdn
}

output "deployable_components" {
  description = "What `m deploy-mcp` ships, in the same shape as the services configuration's output."
  value = {
    "mcp-server-rest" = {
      cloud_run_name = module.mcp-server.cloud_run_name
      command        = "run-server-rest"
      kind           = "service"
    }
  }
}
