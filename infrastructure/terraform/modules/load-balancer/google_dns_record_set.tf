resource "google_dns_record_set" "api" {
  # project is the operations project, so we leave it blank
  name         = join("", [var.feature_environment, var.domain_name, "."])
  type         = "A"
  ttl          = 300
  managed_zone = var.dns_managed_zone
  rrdatas      = [google_compute_global_address.global-ip-address.address]
}
