resource "google_compute_target_https_proxy" "target-https-proxy" {
  project         = var.project_id
  name            = "${var.feature_environment}${var.service_name}-target-https-proxy"
  description     = "Target HTTPS proxy for the ${var.service_name} service."
  certificate_map = "//certificatemanager.googleapis.com/${google_certificate_manager_certificate_map.certificate-map.id}"
  url_map         = google_compute_url_map.url-map.self_link
}
