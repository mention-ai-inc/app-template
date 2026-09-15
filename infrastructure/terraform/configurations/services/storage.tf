module "cache-containers" {
  for_each = var.services
  source   = "../../modules/storage-container"

  storage_account_id  = local.storage_account_id
  feature_environment = local.feature_environment
  service             = each.key
  container_name      = "cache"
  principal_ids       = [module.service-identity[each.key].principal_id]
}

module "event-archive-container" {
  source = "../../modules/storage-container"

  storage_account_id  = local.storage_account_id
  feature_environment = local.feature_environment
  container_name      = "event-archive"
  principal_ids       = [for service in keys(var.services) : module.service-identity[service].principal_id]
}

module "audit-archive-container" {
  source = "../../modules/storage-container"

  storage_account_id  = local.storage_account_id
  feature_environment = local.feature_environment
  container_name      = "audit-archive"
  principal_ids       = [for service in keys(var.services) : module.service-identity[service].principal_id]
}

resource "azurerm_storage_container_immutability_policy" "audit-archive" {
  storage_container_resource_manager_id = module.audit-archive-container.resource_manager_id
  immutability_period_in_days           = var.audit_retention_days
  protected_append_writes_all_enabled   = true
  locked                                = local.is_production
}

resource "azurerm_role_assignment" "service-static-assets-reader" {
  for_each = var.services

  scope                = local.operations.static_assets_container_id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = module.service-identity[each.key].principal_id
  principal_type       = "ServicePrincipal"
}
