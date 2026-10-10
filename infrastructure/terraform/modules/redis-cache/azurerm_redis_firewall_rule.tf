resource "azurerm_redis_firewall_rule" "allowed" {
  for_each = { for rule in var.firewall_rules : rule.name => rule }

  name                = each.value.name
  redis_cache_name    = azurerm_redis_cache.cache.name
  resource_group_name = var.resource_group_name
  start_ip            = each.value.start_ip
  end_ip              = each.value.end_ip
}
