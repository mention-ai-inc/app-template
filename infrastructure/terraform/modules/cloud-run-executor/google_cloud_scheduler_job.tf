resource "google_cloud_scheduler_job" "keep-alive" {
  project     = var.project_id
  region      = var.region
  name        = "${google_cloud_run_v2_service.executor.name}-keep-alive"
  description = "Health check ${var.service_name}-${var.command_name} by pinging the health endpoint every ${var.health_check_interval_minutes} minutes."
  schedule    = "*/${var.health_check_interval_minutes} * * * *"
  time_zone   = "Etc/UTC"

  http_target {
    uri         = "${google_cloud_run_v2_service.executor.uri}/health"
    http_method = "GET"
    oidc_token {
      service_account_email = var.service_account_email
    }
  }
}
