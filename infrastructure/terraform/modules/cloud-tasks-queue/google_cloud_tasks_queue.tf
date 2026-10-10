resource "random_id" "queue_id" {
  byte_length = 4
}

resource "google_cloud_tasks_queue" "queue" {
  name     = "${var.feature_environment}${var.service_name}-${replace(var.command_name, "_", "-")}-${random_id.queue_id.hex}"
  project  = var.project_id
  location = var.region

  rate_limits {
    max_concurrent_dispatches = var.task_concurrency
    max_dispatches_per_second = var.max_tasks_per_second
  }

  retry_config {
    max_attempts  = var.max_task_attempts
    min_backoff   = "${var.minimum_backoff_seconds}s"
    max_backoff   = "${var.maximum_backoff_seconds}s"
    max_doublings = var.maximum_doublings
  }
}
