data "aws_secretsmanager_secret" "clerk-secret-key" {
  name = "CLERK_SECRET_KEY"
}

data "aws_secretsmanager_secret" "clerk-webhook-secret" {
  name = "CLERK_WEBHOOK_SECRET"
}

data "aws_secretsmanager_secret" "gemini-api-key" {
  name = "GEMINI_API_KEY"
}

data "aws_secretsmanager_secret" "logfire-write-token" {
  name = "LOGFIRE_WRITE_TOKEN"
}

data "aws_secretsmanager_secret" "sentry-dsn" {
  name = "SENTRY_DSN"
}

data "aws_secretsmanager_secret_version" "redis-auth-token" {
  secret_id = data.terraform_remote_state.operations.outputs.redis_auth_token_secret_arn
}

locals {
  secret_variables = {
    "REDIS_PASSWORD"       = data.terraform_remote_state.operations.outputs.redis_auth_token_secret_arn
    "CLERK_SECRET_KEY"     = data.aws_secretsmanager_secret.clerk-secret-key.arn
    "CLERK_WEBHOOK_SECRET" = data.aws_secretsmanager_secret.clerk-webhook-secret.arn
    "GEMINI_API_KEY"       = data.aws_secretsmanager_secret.gemini-api-key.arn
    "SENTRY_DSN"           = data.aws_secretsmanager_secret.sentry-dsn.arn
    "LOGFIRE_WRITE_TOKEN"  = data.aws_secretsmanager_secret.logfire-write-token.arn
  }
}
