output "engineers_members" {
  description = "Sign-in addresses of the engineers, used where an application needs a human-readable allowlist."
  value       = local.engineers.members
}

output "engineers_object_ids" {
  description = "Directory object IDs of the engineers. Azure role assignments address principals by object ID rather than by address, so these are what a role assignment grants to."
  value       = local.engineers.object_ids
}

output "engineers_roles" {
  value = {
    production = local.engineers.roles.host,
    feature    = concat(local.engineers.roles.host, local.engineers.roles.feature_only)
    operations = local.engineers.roles.operations
  }
}

output "service_roles" {
  value = {
    host = {
      for service in var.services : service => concat(local.services.common_roles.host, lookup(local.services.individual_roles, service, { host = [] }).host)
    },
    operations = {
      for service in var.services : service => concat(local.services.common_roles.operations, lookup(local.services.individual_roles, service, { operations = [] }).operations)
    }
  }
}

output "github_actions_roles" {
  value = {
    host         = local.github_actions.roles.host,
    feature_only = local.github_actions.roles.feature_only,
    operations   = local.github_actions.roles.operations
  }
}

output "cosmos_data_roles" {
  description = "Cosmos DB built-in data-plane role definition IDs. Data access is not granted by an Azure RBAC role assignment, so these are used with azurerm_cosmosdb_sql_role_assignment instead."
  value       = local.cosmos_data_roles
}
