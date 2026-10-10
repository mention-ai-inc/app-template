resource "google_certificate_manager_certificate_map" "certificate-map" {
  project     = var.project_id
  name        = "${var.feature_environment}certificate-map"
  description = "Load balancer authorization certificate map: https://cloud.google.com/certificate-manager/docs/deploy-google-managed-lb-auth"
}
