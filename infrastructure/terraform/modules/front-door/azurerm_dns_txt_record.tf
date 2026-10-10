resource "azurerm_dns_txt_record" "api-domain-validation" {
  name                = "_dnsauth.${local.api_dns_record_name}"
  zone_name           = var.dns_zone_name
  resource_group_name = var.dns_zone_resource_group_name
  ttl                 = 3600

  record {
    value = azurerm_cdn_frontdoor_custom_domain.api.validation_token
  }
}
