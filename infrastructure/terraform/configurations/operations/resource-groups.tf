resource "azurerm_resource_group" "production" {
  name     = var.production_resource_group_name
  location = var.preferred_region
}

resource "azurerm_resource_group" "feature" {
  name     = var.feature_resource_group_name
  location = var.preferred_region
}

output "operations_resource_group_name" {
  value = data.azurerm_resource_group.operations.name
}

output "operations_resource_group_id" {
  value = data.azurerm_resource_group.operations.id
}

output "production_resource_group_name" {
  value = azurerm_resource_group.production.name
}

output "production_resource_group_id" {
  value = azurerm_resource_group.production.id
}

output "feature_resource_group_name" {
  value = azurerm_resource_group.feature.name
}

output "feature_resource_group_id" {
  value = azurerm_resource_group.feature.id
}
