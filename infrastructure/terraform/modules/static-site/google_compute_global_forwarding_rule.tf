resource "google_compute_global_forwarding_rule" "https_forwarding_rule" {
  project               = var.project_id
  name                  = "${replace(var.bucket_name, "--", "-")}-https-rule"
  description           = "HTTPS forwarding rule for ${var.domain_name} static site"
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  port_range            = "443"
  target                = google_compute_target_https_proxy.https_proxy.self_link
  ip_address            = google_compute_global_address.global_ip.address
}

# Optional HTTP to HTTPS redirect
resource "google_compute_url_map" "http_redirect" {
  project = var.project_id
  name    = "${replace(var.bucket_name, "--", "-")}-http-redirect"

  default_url_redirect {
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
    https_redirect         = true
  }
}

resource "google_compute_target_http_proxy" "http_proxy" {
  project = var.project_id
  name    = "${replace(var.bucket_name, "--", "-")}-http-proxy"
  url_map = google_compute_url_map.http_redirect.self_link
}

resource "google_compute_global_forwarding_rule" "http_forwarding_rule" {
  project               = var.project_id
  name                  = "${replace(var.bucket_name, "--", "-")}-http-rule"
  description           = "HTTP to HTTPS redirect for ${var.domain_name} static site"
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  port_range            = "80"
  target                = google_compute_target_http_proxy.http_proxy.self_link
  ip_address            = google_compute_global_address.global_ip.address
} 