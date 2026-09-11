resource "google_dns_managed_zone" "zone" {
  name        = "acme"
  dns_name    = "acme.mentionai.app."
  description = "DNS zone for acme.mentionai.app."
}

resource "google_dns_record_set" "apex" {
  name         = "acme.mentionai.app."
  type         = "A"
  ttl          = "300"
  managed_zone = google_dns_managed_zone.zone.name
  rrdatas      = ["0.0.0.0"]
}

output "dns_zone_name" {
  value = google_dns_managed_zone.zone.name
}
