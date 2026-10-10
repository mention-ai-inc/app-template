resource "google_cloud_scheduler_job" "schedule" {
  count = var.schedule != "" ? 1 : 0

  project     = var.project_id
  region      = var.region
  name        = "${var.feature_environment}${var.service_name}-${replace(var.job_name, "_", "-")}-schedule"
  description = "Invocation schedule for ${var.service_name}-${var.job_name} job."
  schedule    = var.schedule
  time_zone   = "Etc/UTC"

  http_target {
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_number}/jobs/${google_cloud_run_v2_job.cloud-run-service-job.name}:run"
    http_method = "POST"

    oauth_token {
      service_account_email = var.service_account_email
    }
  }
}
