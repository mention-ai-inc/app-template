locals {
  environment_secrets = merge({
    "CLERK_SECRET_KEY" = "CLERK-SECRET-KEY"
    "GEMINI_API_KEY"   = "GEMINI-API-KEY"
  }, var.enable_logfire ? { LOGFIRE_WRITE_TOKEN = "LOGFIRE-WRITE-TOKEN" } : {})

  shared_secrets = var.enable_sentry ? {
    "SENTRY_DSN" = "SENTRY-DSN"
  } : {}

  secret_env = merge(
    { for variable, secret in local.environment_secrets : variable => "${local.key_vault_uri}secrets/${secret}" },
    { for variable, secret in local.shared_secrets : variable => "${local.operations.operations_key_vault_uri}secrets/${secret}" },
    { "REDIS_PASSWORD" = azurerm_key_vault_secret.redis-password.versionless_id },
  )
}
