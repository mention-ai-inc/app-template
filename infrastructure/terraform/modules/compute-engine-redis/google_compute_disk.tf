resource "google_compute_disk" "redis_data" {
  project = var.project_id
  zone    = var.zone
  name    = "${var.environment_prefix}redis-data"
  type    = "pd-ssd"
  size    = var.disk_size_gb
}
