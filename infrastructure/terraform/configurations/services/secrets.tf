# project specific secrets
data "google_secret_manager_secret_version_access" "clerk-secret-key" {
  project = local.project
  secret  = "CLERK_SECRET_KEY"
}


data "google_secret_manager_secret_version_access" "gemini-api-key" {
  project = local.project
  secret  = "GEMINI_API_KEY"
}

data "google_secret_manager_secret_version_access" "logfire-write-token" {
  count   = var.enable_logfire ? 1 : 0
  project = local.project
  secret  = "LOGFIRE_WRITE_TOKEN"
}

# shared secrets
data "google_secret_manager_secret_version_access" "sentry-dsn" {
  count   = var.enable_sentry ? 1 : 0
  project = var.operations_project_id
  secret  = "SENTRY_DSN"
}
