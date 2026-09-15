module "permissions" {
  source = "../../modules/permissions"

  services = keys(var.services)
}

module "service-identity" {
  source   = "../../modules/managed-identity"
  for_each = toset(keys(var.services))

  name                = "${local.feature_environment}${each.value}-s"
  resource_group_name = local.resource_group_name
  location            = var.preferred_region

  role_assignments = concat(
    [for role in lookup(module.permissions.service_roles.host, each.value, []) : {
      role  = role
      scope = local.resource_group_id
    }],
    [for role in lookup(module.permissions.service_roles.operations, each.value, []) : {
      role  = role
      scope = local.operations.operations_resource_group_id
    }],
  )
}

resource "azurerm_cosmosdb_sql_role_assignment" "service-data" {
  for_each = toset(keys(var.services))

  resource_group_name = local.resource_group_name
  account_name        = local.cosmos_account_name
  role_definition_id  = "${local.cosmos_account_id}/sqlRoleDefinitions/${module.permissions.cosmos_data_roles.contributor}"
  principal_id        = module.service-identity[each.value].principal_id
  scope               = "${local.cosmos_account_id}/dbs/${azurerm_cosmosdb_sql_database.services.name}"
}

module "default-identity" {
  source = "../../modules/managed-identity"

  name                = "${local.feature_environment}default"
  resource_group_name = local.resource_group_name
  location            = var.preferred_region

  role_assignments = [
    {
      role  = "Reader"
      scope = local.resource_group_id
    },
    {
      role  = "AcrPull"
      scope = local.operations.operations_resource_group_id
    },
  ]
}
