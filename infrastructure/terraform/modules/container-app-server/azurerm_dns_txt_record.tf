resource "azurerm_dns_txt_record" "server-domain-verification" {
  count = local.has_custom_domain ? 1 : 0

  name                = "asuid.${var.dns_record_name}"
  zone_name           = var.dns_zone_name
  resource_group_name = var.dns_zone_resource_group_name
  ttl                 = 300

  record {
    value = azurerm_container_app.server.custom_domain_verification_id
  }
}
