resource "google_compute_backend_service" "backend-service" {
  project               = var.project_id
  name                  = "${var.feature_environment}${var.service_name}-backend-service${var.backend_service_name_suffix}"
  description           = "Backend service for the ${var.service_name} service."
  session_affinity      = var.backend_service_session_affinity
  timeout_sec           = var.backend_service_timeout_seconds
  protocol              = var.backend_service_protocol
  load_balancing_scheme = var.backend_service_load_balancing_scheme
  security_policy       = var.security_policy

  backend {
    balancing_mode = var.backend_service_balancing_mode
    group          = google_compute_region_network_endpoint_group.network-endpoint-group.id
  }

  dynamic "iap" {
    for_each = var.iap_enabled ? [1] : []
    content {
      enabled = true
    }
  }
}
