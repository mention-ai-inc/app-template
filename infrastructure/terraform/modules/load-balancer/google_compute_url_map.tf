resource "google_compute_url_map" "url-map" {
  project         = var.project_id
  name            = "${var.feature_environment}${var.service_name}-url-map"
  description     = "URL map for ${var.service_name}."
  default_service = module.catchall-server.backend_service_self_link

  host_rule {
    hosts        = [join("", [var.feature_environment, var.domain_name])]
    path_matcher = "${var.feature_environment}${var.service_name}-path-matcher"
  }

  path_matcher {
    name            = "${var.feature_environment}${var.service_name}-path-matcher"
    default_service = module.catchall-server.backend_service_self_link

    dynamic "path_rule" {
      for_each = var.rest_service_links

      content {
        paths   = ["/rest/${path_rule.key}/*"]
        service = path_rule.value
      }
    }
  }
}
