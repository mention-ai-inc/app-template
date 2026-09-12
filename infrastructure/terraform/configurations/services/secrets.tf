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

data "google_secret_manager_secret_version_access" "logfire-write-token" {
  project = local.project
  secret  = "LOGFIRE_WRITE_TOKEN"
}

# shared secrets
data "google_secret_manager_secret_version_access" "sentry-dsn" {
  project = var.operations_project_id
  secret  = "SENTRY_DSN"
}
