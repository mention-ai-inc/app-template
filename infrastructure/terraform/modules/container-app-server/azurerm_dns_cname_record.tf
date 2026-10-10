resource "azurerm_dns_cname_record" "server" {
  count = local.has_custom_domain ? 1 : 0

  name                = var.dns_record_name
  zone_name           = var.dns_zone_name
  resource_group_name = var.dns_zone_resource_group_name
  ttl                 = 300
  record              = azurerm_container_app.server.ingress[0].fqdn
}
