resource "google_compute_target_https_proxy" "https_proxy" {
  project         = var.project_id
  name            = "${replace(var.bucket_name, "--", "-")}-https-proxy"
  description     = "HTTPS proxy for ${var.domain_name} static site"
  url_map         = google_compute_url_map.url_map.self_link
  certificate_map = "//certificatemanager.googleapis.com/${google_certificate_manager_certificate_map.certificate_map.id}"
} 