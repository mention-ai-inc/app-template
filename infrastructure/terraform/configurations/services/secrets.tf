data "aws_secretsmanager_secret" "clerk-secret-key" {
  name = local.is_production ? "production/CLERK_SECRET_KEY" : "feature/CLERK_SECRET_KEY"
}


data "aws_secretsmanager_secret" "gemini-api-key" {
  name = "GEMINI_API_KEY"
}

data "aws_secretsmanager_secret" "logfire-write-token" {
  count = var.enable_logfire ? 1 : 0
  name  = "LOGFIRE_WRITE_TOKEN"
}

data "aws_secretsmanager_secret" "sentry-dsn" {
  count = var.enable_sentry ? 1 : 0
  name  = "SENTRY_DSN"
}

data "aws_secretsmanager_secret_version" "redis-auth-token" {
  secret_id = data.terraform_remote_state.operations.outputs.redis_auth_token_secret_arn
}

locals {
  secret_variables = merge({
    "REDIS_PASSWORD"   = data.terraform_remote_state.operations.outputs.redis_auth_token_secret_arn
    "CLERK_SECRET_KEY" = data.aws_secretsmanager_secret.clerk-secret-key.arn
    "GEMINI_API_KEY"   = data.aws_secretsmanager_secret.gemini-api-key.arn
    },
    var.enable_sentry ? { SENTRY_DSN = data.aws_secretsmanager_secret.sentry-dsn[0].arn } : {},
    var.enable_logfire ? { LOGFIRE_WRITE_TOKEN = data.aws_secretsmanager_secret.logfire-write-token[0].arn } : {},
  )
}
