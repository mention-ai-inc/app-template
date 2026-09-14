resource "google_certificate_manager_certificate_map_entry" "certificate-map-entry" {
  project      = var.project_id
  name         = "${var.feature_environment}certificate-map-entry"
  description  = "Load balancer authorization certificate map entry: https://cloud.google.com/certificate-manager/docs/deploy-google-managed-lb-auth"
  map          = google_certificate_manager_certificate_map.certificate-map.name
  certificates = [google_certificate_manager_certificate.ssl-certificate.id]
  hostname     = join("", [var.feature_environment, var.domain_name])
}
