# Create DNS A records for all domains
resource "google_dns_record_set" "domain_records" {
  for_each = toset(local.all_domains)

  project      = var.project_id
  managed_zone = var.dns_managed_zone
  name         = "${each.value}."
  type         = "A"
  ttl          = 300

  rrdatas = [google_compute_global_address.global_ip.address]
}