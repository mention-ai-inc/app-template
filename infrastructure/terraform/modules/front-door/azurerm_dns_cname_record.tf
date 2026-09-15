resource "azurerm_dns_cname_record" "api" {
  name                = local.api_dns_record_name
  zone_name           = var.dns_zone_name
  resource_group_name = var.dns_zone_resource_group_name
  ttl                 = 300
  record              = azurerm_cdn_frontdoor_endpoint.api.host_name

  depends_on = [
    azurerm_dns_txt_record.api-domain-validation,
    azurerm_cdn_frontdoor_route.service,
    azurerm_cdn_frontdoor_route.catchall,
  ]
}
