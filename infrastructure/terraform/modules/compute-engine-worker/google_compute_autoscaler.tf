resource "google_compute_autoscaler" "autoscaler" {
  project = var.project_id
  zone    = var.zone
  name    = "${var.feature_environment}${replace(var.service_name, "_", "-")}${replace(var.worker_name, "_", "-")}autoscaler"
  target  = google_compute_instance_group_manager.instance-group-manager.self_link

  autoscaling_policy {
    min_replicas    = var.minimum_instances
    max_replicas    = var.maximum_instances
    cooldown_period = var.cooldown_period

    cpu_utilization {
      target = var.target_cpu_utilization
    }
  }
}
