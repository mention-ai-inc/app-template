resource "google_compute_instance_group_manager" "instance-group-manager" {
  project            = var.project_id
  zone               = var.zone
  name               = join("", [var.feature_environment, replace(var.service_name, "_", "-"), "-worker-", replace(var.worker_name, "_", "-")])
  base_instance_name = join("", [var.feature_environment, replace(var.service_name, "_", "-"), "-worker-", replace(var.worker_name, "_", "-")])
  description        = "Instance group manager for the ${var.feature_environment}${var.service_name}-${var.worker_name} worker."

  version {
    instance_template = google_compute_instance_template.instance-template.self_link
  }

  lifecycle {
    ignore_changes = [
      version[0].name,
    ]
  }
}
