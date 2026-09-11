resource "google_certificate_manager_certificate_map" "certificate_map" {
  project     = var.project_id
  name        = "${replace(var.bucket_name, "--", "-")}-cert-map"
  description = "Certificate map for ${var.domain_name} static site"

  labels = {
    domain     = replace(var.domain_name, ".", "-")
    module     = "static-site"
    managed_by = "terraform"
  }
} 