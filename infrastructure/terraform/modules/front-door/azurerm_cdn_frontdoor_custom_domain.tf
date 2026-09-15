resource "azurerm_cdn_frontdoor_custom_domain" "api" {
  name                     = local.sanitised_fqdn
  cdn_frontdoor_profile_id = var.profile_id
  host_name                = local.api_fqdn
  dns_zone_id              = var.dns_zone_id

  tls {
    certificate_type = "ManagedCertificate"
    minimum_version  = "TLS12"
  }
}
