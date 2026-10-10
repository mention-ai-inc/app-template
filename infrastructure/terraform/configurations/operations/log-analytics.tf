resource "azurerm_log_analytics_workspace" "production" {
  name                = "${var.production_resource_group_name}-logs"
  resource_group_name = azurerm_resource_group.production.name
  location            = var.preferred_region
  sku                 = "PerGB2018"
  retention_in_days   = var.production_log_retention_days
}

resource "azurerm_log_analytics_workspace" "feature" {
  name                = "${var.feature_resource_group_name}-logs"
  resource_group_name = azurerm_resource_group.feature.name
  location            = var.preferred_region
  sku                 = "PerGB2018"
  retention_in_days   = var.feature_log_retention_days
}

output "production_log_analytics_workspace_id" {
  value = azurerm_log_analytics_workspace.production.id
}

output "feature_log_analytics_workspace_id" {
  value = azurerm_log_analytics_workspace.feature.id
}

output "production_log_analytics_customer_id" {
  description = "The workspace GUID the Log Analytics query API addresses, which is not the ARM resource id."
  value       = azurerm_log_analytics_workspace.production.workspace_id
}

output "feature_log_analytics_customer_id" {
  description = "The workspace GUID the Log Analytics query API addresses, which is not the ARM resource id."
  value       = azurerm_log_analytics_workspace.feature.workspace_id
}
