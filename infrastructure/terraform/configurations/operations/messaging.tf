resource "azurerm_servicebus_namespace" "production" {
  name                = var.production_servicebus_namespace_name
  resource_group_name = azurerm_resource_group.production.name
  location            = var.preferred_region
  sku                 = "Standard"
  local_auth_enabled  = false
  minimum_tls_version = "1.2"
}

resource "azurerm_servicebus_namespace" "feature" {
  name                = var.feature_servicebus_namespace_name
  resource_group_name = azurerm_resource_group.feature.name
  location            = var.preferred_region
  sku                 = "Standard"
  local_auth_enabled  = false
  minimum_tls_version = "1.2"
}

output "production_servicebus_namespace_id" {
  value = azurerm_servicebus_namespace.production.id
}

output "production_servicebus_namespace_name" {
  value = azurerm_servicebus_namespace.production.name
}

output "production_servicebus_namespace_hostname" {
  value = "${azurerm_servicebus_namespace.production.name}.servicebus.windows.net"
}

output "feature_servicebus_namespace_id" {
  value = azurerm_servicebus_namespace.feature.id
}

output "feature_servicebus_namespace_name" {
  value = azurerm_servicebus_namespace.feature.name
}

output "feature_servicebus_namespace_hostname" {
  value = "${azurerm_servicebus_namespace.feature.name}.servicebus.windows.net"
}
