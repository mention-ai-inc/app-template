resource "azurerm_container_app_environment" "production" {
  name                       = var.production_container_app_environment_name
  resource_group_name        = azurerm_resource_group.production.name
  location                   = var.preferred_region
  log_analytics_workspace_id = azurerm_log_analytics_workspace.production.id
  logs_destination           = "log-analytics"
}

resource "azurerm_container_app_environment" "feature" {
  name                       = var.feature_container_app_environment_name
  resource_group_name        = azurerm_resource_group.feature.name
  location                   = var.preferred_region
  log_analytics_workspace_id = azurerm_log_analytics_workspace.feature.id
  logs_destination           = "log-analytics"
}

output "production_container_app_environment_id" {
  value = azurerm_container_app_environment.production.id
}

output "production_container_app_environment_default_domain" {
  value = azurerm_container_app_environment.production.default_domain
}

output "feature_container_app_environment_id" {
  value = azurerm_container_app_environment.feature.id
}

output "feature_container_app_environment_default_domain" {
  value = azurerm_container_app_environment.feature.default_domain
}
