resource "google_compute_global_address" "global-ip-address" {
  project      = var.project_id
  name         = "${var.feature_environment}${var.service_name}-global-ip-address"
  description  = "Global IP Address for the ${var.service_name} API."
  address_type = var.global_address_type
  ip_version   = var.global_address_ip_version
}
