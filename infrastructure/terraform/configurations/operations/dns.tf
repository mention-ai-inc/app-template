resource "google_dns_managed_zone" "zone" {
  name        = "acme"
  dns_name    = "acme.example.com."
  description = "DNS zone for acme.example.com."
}

resource "google_dns_record_set" "apex" {
  name         = "acme.example.com."
  type         = "A"
  ttl          = "300"
  managed_zone = google_dns_managed_zone.zone.name
  rrdatas      = ["0.0.0.0"]
}

output "dns_zone_name" {
  value = google_dns_managed_zone.zone.name
}
