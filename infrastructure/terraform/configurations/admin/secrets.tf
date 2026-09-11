data "google_secret_manager_secret_version_access" "redis-password" {
  secret = data.terraform_remote_state.operations.outputs.redis-password-secret-id
}

# project specific secrets
data "google_secret_manager_secret_version_access" "clerk-secret-key" {
  project = local.project
  secret  = "CLERK_SECRET_KEY"
}

data "google_secret_manager_secret_version_access" "clerk-webhook-secret" {
  project = local.project
  secret  = "CLERK_WEBHOOK_SECRET"
}

data "google_secret_manager_secret_version_access" "gemini-api-key" {
  project = local.project
  secret  = "GEMINI_API_KEY"
}

data "google_secret_manager_secret_version_access" "sentry-dsn" {
  project = local.project
  secret  = "SENTRY_DSN"
}

data "google_secret_manager_secret_version_access" "logfire-write-token" {
  project = local.project
  secret  = "LOGFIRE_WRITE_TOKEN"
}

data "google_secret_manager_secret_version_access" "iap-oauth-client-id" {
  project = local.project
  secret  = "ADMIN_IAP_OAUTH_CLIENT_ID"
}

data "google_secret_manager_secret_version_access" "iap-oauth-client-secret" {
  project = local.project
  secret  = "ADMIN_IAP_OAUTH_CLIENT_SECRET"
}
