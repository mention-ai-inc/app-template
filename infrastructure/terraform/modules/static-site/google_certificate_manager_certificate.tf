resource "google_certificate_manager_certificate" "ssl_certificate" {
  project     = var.project_id
  name        = "${replace(var.bucket_name, "--", "-")}-ssl-cert"
  description = "SSL certificate for ${var.domain_name} static site"
  location    = "global"

  managed {
    domains = local.all_domains
  }

  labels = {
    domain     = replace(var.domain_name, ".", "-")
    module     = "static-site"
    managed_by = "terraform"
  }
} 