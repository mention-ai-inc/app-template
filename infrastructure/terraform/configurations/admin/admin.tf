locals {
  env_variables = {
    "CLERK_JWKS_URL"        = module.environment.settings.tokens.clerk_jwks_url
    "AWS_REGION"            = var.preferred_region
    "AWS_ACCOUNT_ID"        = local.account_id
    "FEATURE_ENVIRONMENT"   = local.feature_environment
    "PYTHONWARNINGS"        = var.python_warnings
    "REDIS_HOST"            = data.terraform_remote_state.services.outputs.redis_internal_ip
    "REDIS_PORT"            = tostring(data.terraform_remote_state.services.outputs.redis_port)
    "REDIS_TLS"             = "true"
    "DYNAMODB_TABLE_NAME"   = data.terraform_remote_state.services.outputs.dynamodb_table_name
    "EVENT_TOPIC_ARNS_JSON" = jsonencode(data.terraform_remote_state.services.outputs.topic_arns)
    "SERVICE"               = "admin"
  }

  staff_allowlist = module.permissions.engineers_members
}

module "admin-docker-images" {
  source = "../../modules/ecr-repository"

  repository_name = "${local.feature_environment}admin"
  readers         = [module.admin-task-role.arn, module.task-execution-role.arn]
}

module "admin-backfill-job" {
  source = "../../modules/ecs-job"

  region              = var.preferred_region
  feature_environment = local.feature_environment
  cluster_arn         = local.cluster_arn
  service_name        = "admin"
  job_name            = "backfill"

  command              = ["admin", "backfill"]
  max_retries          = 0
  task_timeout_seconds = 3600
  cpu                  = "1024"
  memory               = "2048"
  log_retention_days   = var.log_retention_days

  task_role_arn      = module.admin-task-role.arn
  execution_role_arn = module.task-execution-role.arn

  vpc_id     = local.vpc_id
  subnet_ids = local.private_subnet_ids

  env     = local.env_variables
  secrets = local.secret_variables
}

module "admin-seed-job" {
  count  = local.is_production ? 0 : 1
  source = "../../modules/ecs-job"

  region              = var.preferred_region
  feature_environment = local.feature_environment
  cluster_arn         = local.cluster_arn
  service_name        = "admin"
  job_name            = "seed"

  command              = ["admin", "seed"]
  max_retries          = 0
  task_timeout_seconds = 21600
  cpu                  = "1024"
  memory               = "2048"
  log_retention_days   = var.log_retention_days

  task_role_arn      = module.admin-task-role.arn
  execution_role_arn = module.task-execution-role.arn

  vpc_id     = local.vpc_id
  subnet_ids = local.private_subnet_ids

  env     = local.env_variables
  secrets = local.secret_variables
}

module "admin-audit-trigger" {
  source = "../../modules/dynamodb-stream-trigger"

  feature_environment = local.feature_environment
  service_name        = "admin"
  trigger_name        = "publish_audit_event"

  collection       = "audit"
  table_stream_arn = data.terraform_remote_state.services.outputs.dynamodb_table_stream_arn
  reader_role_arns = [module.admin-task-role.arn]
}

module "admin-trigger-pool" {
  source = "../../modules/ecs-pool"

  region              = var.preferred_region
  feature_environment = local.feature_environment
  cluster_arn         = local.cluster_arn
  cluster_name        = local.cluster_name
  service_name        = "admin"
  pool_name           = "triggers"
  component_type      = "trigger"

  task_role_arn      = module.admin-task-role.arn
  execution_role_arn = module.task-execution-role.arn

  minimum_instances   = 1
  maximum_instances   = 5
  backlog_queue_names = [module.admin-audit-trigger.queue_name]
  log_retention_days  = var.log_retention_days

  vpc_id     = local.vpc_id
  subnet_ids = local.private_subnet_ids

  env = merge(local.env_variables, {
    "SQS_TRIGGER_QUEUES_JSON" = jsonencode({
      "admin:publish_audit_event" = module.admin-audit-trigger.queue_url
    })
  })
  secrets = local.secret_variables
}

module "admin-target-group-name" {
  source = "../../modules/resource-name"

  full_name  = "${local.feature_environment}admin-s-rest"
  max_length = 32
}

module "admin-server" {
  source = "../../modules/ecs-server"

  region              = var.preferred_region
  feature_environment = local.feature_environment
  cluster_arn         = local.cluster_arn
  cluster_name        = local.cluster_name
  service_name        = "admin"
  server_name         = "rest"

  task_role_arn      = module.admin-task-role.arn
  execution_role_arn = module.task-execution-role.arn

  cpu                       = "512"
  memory                    = "1024"
  container_concurrency     = 80
  timeout_seconds           = 300
  minimum_instances         = 1
  maximum_instances         = 3
  health_check_request_path = "/health"
  log_retention_days        = var.log_retention_days

  vpc_id                          = local.vpc_id
  subnet_ids                      = local.private_subnet_ids
  load_balancer_security_group_id = module.admin-load-balancer.security_group_id
  target_group_arn                = module.admin-load-balancer.default_target_group_arn

  env = merge(local.env_variables, {
    "STAFF_ALLOWLIST"        = join(",", local.staff_allowlist)
    "ECS_CLUSTER_ARN"        = local.cluster_arn
    "ECS_SUBNET_IDS"         = join(",", local.private_subnet_ids)
    "ECS_SECURITY_GROUP_IDS" = module.admin-backfill-job.security_group_id
  })
  secrets = local.secret_variables
}

module "admin-load-balancer" {
  source = "../../modules/application-load-balancer"

  feature_environment = local.feature_environment
  surface_name        = "admin"
  domain_name         = "${var.admin_subdomain}.${var.domain_name}"
  hosted_zone_id      = local.hosted_zone_id

  vpc_id     = local.vpc_id
  subnet_ids = local.public_subnet_ids

  default_service = {
    target_group_name                = module.admin-target-group-name.name
    container_port                   = 8080
    health_check_request_path        = "/health"
    deregistration_delay_seconds     = 30
    health_check_interval_seconds    = 30
    health_check_timeout_seconds     = 5
    health_check_healthy_threshold   = 2
    health_check_unhealthy_threshold = 3
  }
  deletion_protection_enabled = local.is_production
  web_acl_arn                 = aws_wafv2_web_acl.admin.arn
  access_log_bucket           = data.terraform_remote_state.operations.outputs.load_balancer_logs_bucket_name

  authenticate_oidc = {
    issuer                 = var.oidc_issuer
    authorization_endpoint = var.oidc_authorization_endpoint
    token_endpoint         = var.oidc_token_endpoint
    user_info_endpoint     = var.oidc_user_info_endpoint
    client_id              = data.aws_secretsmanager_secret_version.oidc-client-id.secret_string
    client_secret          = data.aws_secretsmanager_secret_version.oidc-client-secret.secret_string
    scope                  = var.oidc_scope
    session_timeout        = var.oidc_session_timeout_seconds
  }
}

output "admin_fqdn" {
  description = "Hostname the admin API is served on."
  value       = module.admin-load-balancer.fqdn
}

output "deployable_components" {
  description = "What `m deploy-admin` ships, in the same shape as the services configuration's output."
  value = merge(
    {
      "admin-server-rest" = {
        cloud_run_name = module.admin-server.cloud_run_name
        command        = "run-server-rest"
        kind           = "service"
      }
      "admin-pool-triggers" = {
        cloud_run_name = module.admin-trigger-pool.cloud_run_name
        command        = "run-pool-triggers"
        kind           = "service"
      }
      "admin-job-backfill" = {
        cloud_run_name = module.admin-backfill-job.job_name
        command        = "run-job-backfill"
        kind           = "job"
      }
    },
    local.is_production ? {} : {
      "admin-job-seed" = {
        cloud_run_name = module.admin-seed-job[0].job_name
        command        = "run-job-seed"
        kind           = "job"
      }
    },
  )
}
