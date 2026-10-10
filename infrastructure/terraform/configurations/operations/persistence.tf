resource "azurerm_cosmosdb_account" "production" {
  name                = var.production_cosmos_account_name
  resource_group_name = azurerm_resource_group.production.name
  location            = var.preferred_region
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"

  local_authentication_enabled = false
  automatic_failover_enabled   = false
  free_tier_enabled            = false
  minimal_tls_version          = "Tls12"

  consistency_policy {
    consistency_level = "Session"
  }

  geo_location {
    location          = var.preferred_region
    failover_priority = 0
  }

  backup {
    type                = "Periodic"
    interval_in_minutes = 240
    retention_in_hours  = var.production_cosmos_backup_retention_hours
    storage_redundancy  = "Geo"
  }
}

resource "azurerm_cosmosdb_account" "feature" {
  name                = var.feature_cosmos_account_name
  resource_group_name = azurerm_resource_group.feature.name
  location            = var.preferred_region
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"

  local_authentication_enabled = false
  automatic_failover_enabled   = false
  minimal_tls_version          = "Tls12"

  capabilities {
    name = "EnableServerless"
  }

  consistency_policy {
    consistency_level = "Session"
  }

  geo_location {
    location          = var.preferred_region
    failover_priority = 0
  }
}

output "production_cosmos_account_name" {
  value = azurerm_cosmosdb_account.production.name
}

output "production_cosmos_account_id" {
  value = azurerm_cosmosdb_account.production.id
}

output "production_cosmos_endpoint" {
  value = azurerm_cosmosdb_account.production.endpoint
}

output "feature_cosmos_account_name" {
  value = azurerm_cosmosdb_account.feature.name
}

output "feature_cosmos_account_id" {
  value = azurerm_cosmosdb_account.feature.id
}

output "feature_cosmos_endpoint" {
  value = azurerm_cosmosdb_account.feature.endpoint
}
