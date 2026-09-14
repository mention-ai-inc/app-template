resource "google_certificate_manager_certificate" "ssl-certificate" {
  project     = var.project_id
  name        = "${var.feature_environment}ssl-certificate"
  description = "Load balancer authorization certificate: https://cloud.google.com/certificate-manager/docs/deploy-google-managed-lb-auth"

  managed {
    domains = ["${var.feature_environment}${var.domain_name}"]
  }
}
