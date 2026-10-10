resource "azurerm_dns_zone" "zone" {
  name                = var.domain_name
  resource_group_name = data.azurerm_resource_group.operations.name
}

resource "azurerm_dns_a_record" "apex" {
  name                = "@"
  zone_name           = azurerm_dns_zone.zone.name
  resource_group_name = data.azurerm_resource_group.operations.name
  ttl                 = 300
  records             = ["0.0.0.0"]
}

output "dns_zone_id" {
  value = azurerm_dns_zone.zone.id
}

output "dns_zone_name" {
  value = azurerm_dns_zone.zone.name
}

output "dns_zone_resource_group_name" {
  value = data.azurerm_resource_group.operations.name
}

output "dns_zone_name_servers" {
  value = azurerm_dns_zone.zone.name_servers
}
