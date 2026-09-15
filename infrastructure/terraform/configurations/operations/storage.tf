locals {
  storage_accounts = {
    operations = {
      name                = var.operations_storage_account_name
      resource_group_name = data.azurerm_resource_group.operations.name
      replication         = "LRS"
    }
    production = {
      name                = var.production_storage_account_name
      resource_group_name = azurerm_resource_group.production.name
      replication         = "GRS"
    }
    feature = {
      name                = var.feature_storage_account_name
      resource_group_name = azurerm_resource_group.feature.name
      replication         = "LRS"
    }
  }
}

resource "azurerm_storage_account" "account" {
  for_each = local.storage_accounts

  name                            = each.value.name
  resource_group_name             = each.value.resource_group_name
  location                        = var.preferred_region
  account_tier                    = "Standard"
  account_kind                    = "StorageV2"
  account_replication_type        = each.value.replication
  https_traffic_only_enabled      = true
  min_tls_version                 = "TLS1_2"
  shared_access_key_enabled       = false
  default_to_oauth_authentication = true
  allow_nested_items_to_be_public = false

  blob_properties {
    dynamic "cors_rule" {
      for_each = length(var.blob_cors_origins) > 0 ? [1] : []

      content {
        allowed_origins    = var.blob_cors_origins
        allowed_methods    = ["GET", "PUT"]
        allowed_headers    = ["Content-Type"]
        exposed_headers    = ["Content-Type"]
        max_age_in_seconds = 3600
      }
    }
  }
}

resource "azurerm_storage_container" "static-assets" {
  name               = "static-assets"
  storage_account_id = azurerm_storage_account.account["operations"].id
}

output "operations_storage_account_id" {
  value = azurerm_storage_account.account["operations"].id
}

output "operations_storage_account_name" {
  value = azurerm_storage_account.account["operations"].name
}

output "static_assets_container_id" {
  value = azurerm_storage_container.static-assets.id
}

output "production_storage_account_id" {
  value = azurerm_storage_account.account["production"].id
}

output "production_storage_account_name" {
  value = azurerm_storage_account.account["production"].name
}

output "feature_storage_account_id" {
  value = azurerm_storage_account.account["feature"].id
}

output "feature_storage_account_name" {
  value = azurerm_storage_account.account["feature"].name
}
