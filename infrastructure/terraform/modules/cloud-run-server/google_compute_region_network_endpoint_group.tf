resource "google_compute_region_network_endpoint_group" "network-endpoint-group" {
  project               = var.project_id
  name                  = "${var.feature_environment}${replace(var.service_name, "_", "-")}-network-endpoint-group"
  description           = "Network endpoint group for the ${var.service_name} service."
  network_endpoint_type = "SERVERLESS"
  region                = var.region

  cloud_run {
    service = google_cloud_run_v2_service.service.name
  }
}
