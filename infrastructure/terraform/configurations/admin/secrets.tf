locals {
  environment_secrets = {
    "CLERK_SECRET_KEY"     = "CLERK-SECRET-KEY"
    "CLERK_WEBHOOK_SECRET" = "CLERK-WEBHOOK-SECRET"
    "GEMINI_API_KEY"       = "GEMINI-API-KEY"
    "LOGFIRE_WRITE_TOKEN"  = "LOGFIRE-WRITE-TOKEN"
  }

  shared_secrets = {
    "SENTRY_DSN" = "SENTRY-DSN"
  }

  secret_env = merge(
    { for variable, secret in local.environment_secrets : variable => "${local.key_vault_uri}secrets/${secret}" },
    { for variable, secret in local.shared_secrets : variable => "${local.operations.operations_key_vault_uri}secrets/${secret}" },
    { "REDIS_PASSWORD" = local.services.redis_password_secret_id },
  )
}
