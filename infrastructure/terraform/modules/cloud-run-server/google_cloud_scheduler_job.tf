resource "google_cloud_scheduler_job" "keep-alive" {
  count = var.keep_alive_enabled ? 1 : 0

  project     = var.project_id
  region      = var.region
  name        = "${var.feature_environment}${var.service_name}-keep-alive"
  description = "Health check ${var.service_name} by pinging the health endpoint every ${var.health_check_interval_minutes} minutes."
  schedule    = "*/${var.health_check_interval_minutes} * * * *"
  time_zone   = "Etc/UTC"

  http_target {
    uri         = "${google_cloud_run_v2_service.service.uri}${coalesce(var.health_check_request_path, "/${var.server_name}/${var.service_name}/health")}"
    http_method = "GET"
  }
}
