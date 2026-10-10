locals {
  api_fqdn            = join("", [var.feature_environment, var.domain_name])
  api_dns_record_name = trimsuffix(local.api_fqdn, ".${var.dns_zone_name}")
  sanitised_fqdn      = replace(local.api_fqdn, "/[^a-zA-Z0-9]/", "-")
}

resource "azurerm_cdn_frontdoor_endpoint" "api" {
  name                     = "${var.feature_environment}${var.service_name}"
  cdn_frontdoor_profile_id = var.profile_id
  enabled                  = true
}
