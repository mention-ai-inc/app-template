# Create certificate map entries for each domain
resource "google_certificate_manager_certificate_map_entry" "certificate_map_entry" {
  for_each = toset(local.all_domains)

  project      = var.project_id
  name         = "${replace(var.bucket_name, "--", "-")}-${replace(each.value, ".", "-")}-entry"
  description  = "Certificate map entry for ${each.value}"
  map          = google_certificate_manager_certificate_map.certificate_map.name
  certificates = [google_certificate_manager_certificate.ssl_certificate.id]
  hostname     = each.value

  labels = {
    domain     = replace(each.value, ".", "-")
    module     = "static-site"
    managed_by = "terraform"
  }
} 