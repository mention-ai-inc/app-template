locals {
  key_vaults = {
    operations = {
      name                = var.operations_key_vault_name
      resource_group_name = data.azurerm_resource_group.operations.name
      purge_protection    = true
      retention_days      = 90
    }
    production = {
      name                = var.production_key_vault_name
      resource_group_name = azurerm_resource_group.production.name
      purge_protection    = true
      retention_days      = 90
    }
    feature = {
      name                = var.feature_key_vault_name
      resource_group_name = azurerm_resource_group.feature.name
      purge_protection    = false
      retention_days      = 7
    }
  }
}

resource "azurerm_key_vault" "vault" {
  for_each = local.key_vaults

  name                          = each.value.name
  resource_group_name           = each.value.resource_group_name
  location                      = var.preferred_region
  tenant_id                     = var.tenant_id
  sku_name                      = "standard"
  rbac_authorization_enabled    = true
  purge_protection_enabled      = each.value.purge_protection
  soft_delete_retention_days    = each.value.retention_days
  public_network_access_enabled = true
}

output "operations_key_vault_id" {
  value = azurerm_key_vault.vault["operations"].id
}

output "operations_key_vault_uri" {
  value = azurerm_key_vault.vault["operations"].vault_uri
}

output "production_key_vault_id" {
  value = azurerm_key_vault.vault["production"].id
}

output "production_key_vault_uri" {
  value = azurerm_key_vault.vault["production"].vault_uri
}

output "feature_key_vault_id" {
  value = azurerm_key_vault.vault["feature"].id
}

output "feature_key_vault_uri" {
  value = azurerm_key_vault.vault["feature"].vault_uri
}
