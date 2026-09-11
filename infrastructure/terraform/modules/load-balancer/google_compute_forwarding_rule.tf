resource "google_compute_global_forwarding_rule" "forwarding-rule" {
  project               = var.project_id
  name                  = "${var.feature_environment}${var.service_name}-forwarding-rule"
  target                = google_compute_target_https_proxy.target-https-proxy.self_link
  port_range            = var.forwarding_rule_port_range
  load_balancing_scheme = var.forwarding_rule_load_balancing_scheme
  ip_address            = google_compute_global_address.global-ip-address.id
}
