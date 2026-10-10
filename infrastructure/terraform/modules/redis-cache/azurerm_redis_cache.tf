resource "azurerm_redis_cache" "cache" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location
  sku_name            = var.sku_name
  family              = var.family
  capacity            = var.capacity
  tags                = var.tags

  minimum_tls_version           = "1.2"
  non_ssl_port_enabled          = false
  public_network_access_enabled = true

  redis_configuration {
    maxmemory_policy = var.max_memory_policy
  }
}
