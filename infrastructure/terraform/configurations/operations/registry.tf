resource "azurerm_container_registry" "images" {
  name                          = var.container_registry_name
  resource_group_name           = data.azurerm_resource_group.operations.name
  location                      = data.azurerm_resource_group.operations.location
  sku                           = "Standard"
  admin_enabled                 = false
  public_network_access_enabled = true
}

output "container_registry_id" {
  value = azurerm_container_registry.images.id
}

output "container_registry_login_server" {
  value = azurerm_container_registry.images.login_server
}
