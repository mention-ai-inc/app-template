module "permissions" {
  source = "../../modules/permissions"

  services = []
}

module "admin-identity" {
  source = "../../modules/managed-identity"

  name                = "${local.feature_environment}admin-s"
  resource_group_name = local.resource_group_name
  location            = var.preferred_region

  role_assignments = [
    {
      role  = "Reader"
      scope = local.resource_group_id
    },
    {
      role  = "Azure Service Bus Data Receiver"
      scope = local.resource_group_id
    },
    {
      role  = "Azure Service Bus Data Sender"
      scope = local.resource_group_id
    },
    {
      role  = "Key Vault Secrets User"
      scope = local.resource_group_id
    },
    {
      role  = "Monitoring Metrics Publisher"
      scope = local.resource_group_id
    },
    {
      role  = "Storage Blob Data Contributor"
      scope = local.resource_group_id
    },
    {
      role  = "AcrPull"
      scope = local.operations.operations_resource_group_id
    },
    {
      role  = "Key Vault Secrets User"
      scope = local.operations.operations_resource_group_id
    },
  ]
}

resource "azurerm_cosmosdb_sql_role_assignment" "admin-data" {
  resource_group_name = local.resource_group_name
  account_name        = local.cosmos_account_name
  role_definition_id  = "${local.cosmos_account_id}/sqlRoleDefinitions/${module.permissions.cosmos_data_roles.contributor}"
  principal_id        = module.admin-identity.principal_id
  scope               = "${local.cosmos_account_id}/dbs/${local.services.cosmos_database_name}"
}
