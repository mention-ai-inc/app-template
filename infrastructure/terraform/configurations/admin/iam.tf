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
      role  = "Key Vault Crypto User"
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

resource "azurerm_role_definition" "job-operator" {
  name        = "${local.feature_environment}acme-job-operator"
  scope       = local.resource_group_id
  description = "Start container app jobs and read their executions. Reader cannot start a job."

  permissions {
    actions = [
      "Microsoft.App/jobs/read",
      "Microsoft.App/jobs/start/action",
      "Microsoft.App/jobs/executions/read",
    ]
  }

  assignable_scopes = [local.resource_group_id]
}

resource "azurerm_role_assignment" "admin-job-operator" {
  scope              = local.resource_group_id
  role_definition_id = azurerm_role_definition.job-operator.role_definition_resource_id
  principal_id       = module.admin-identity.principal_id
  principal_type     = "ServicePrincipal"
}

resource "azurerm_role_assignment" "admin-log-reader" {
  scope                = local.log_analytics_workspace_id
  role_definition_name = "Log Analytics Reader"
  principal_id         = module.admin-identity.principal_id
  principal_type       = "ServicePrincipal"
}
