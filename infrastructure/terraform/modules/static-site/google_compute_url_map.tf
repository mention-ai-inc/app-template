resource "google_compute_url_map" "url_map" {
  project         = var.project_id
  name            = "${replace(var.bucket_name, "--", "-")}-url-map"
  description     = "URL map for ${var.domain_name} static site with clean URLs"
  default_service = google_compute_backend_bucket.backend.self_link

  # Host rules for all domains
  dynamic "host_rule" {
    for_each = toset(local.all_domains)
    content {
      hosts        = [host_rule.value]
      path_matcher = "main"
    }
  }

  path_matcher {
    name            = "main"
    default_service = google_compute_backend_bucket.backend.self_link

    # Root path serves main page
    path_rule {
      paths = ["/"]
      route_action {
        url_rewrite {
          path_prefix_rewrite = "/${var.main_page_suffix}"
        }
      }
      service = google_compute_backend_bucket.backend.self_link
    }

    # Clean URL mappings (e.g., /pricing -> /pricing.html)
    dynamic "path_rule" {
      for_each = var.clean_url_mappings
      content {
        paths = [path_rule.key]
        route_action {
          url_rewrite {
            path_prefix_rewrite = path_rule.value
          }
        }
        service = google_compute_backend_bucket.backend.self_link
      }
    }

    # Handle directory-style URLs (e.g., /about/ -> /about/index.html)
    dynamic "path_rule" {
      for_each = var.enable_directory_index ? ["enabled"] : []
      content {
        paths = ["*/"]
        route_action {
          url_rewrite {
            path_prefix_rewrite = "/${var.main_page_suffix}"
          }
        }
        service = google_compute_backend_bucket.backend.self_link
      }
    }

    # 404 handling - catch all unmatched paths
    path_rule {
      paths = ["/*"]
      route_action {
        fault_injection_policy {
          abort {
            http_status = 404
            percentage  = 0 # Don't actually abort, just serve from bucket
          }
        }
      }
      service = google_compute_backend_bucket.backend.self_link
    }
  }
} 