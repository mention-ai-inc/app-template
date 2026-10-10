resource "google_dns_record_set" "vercel" {
  name         = "${local.feature_environment}app.acme.example.com."
  type         = "CNAME"
  ttl          = "300"
  managed_zone = data.terraform_remote_state.operations.outputs.dns_zone_name
  rrdatas      = ["cname.vercel-dns.com."]
}
