resource "google_compute_global_address" "global_ip" {
  project      = var.project_id
  name         = "${replace(var.bucket_name, "--", "-")}-global-ip"
  description  = "Global IP address for ${var.domain_name} static site"
  address_type = "EXTERNAL"
  ip_version   = "IPV4"
} 