module "permissions" {
  source = "../../modules/permissions"

  services = []
}

locals {
  subscription_scope = "/subscriptions/${var.subscription_id}"

  environment_scopes = {
    production = azurerm_resource_group.production.id
    feature    = azurerm_resource_group.feature.id
  }

  engineer_environment_roles = {
    for pair in flatten([
      for environment, scope in local.environment_scopes : [
        for role in module.permissions.engineers_roles[environment] : [
          for object_id in module.permissions.engineers_object_ids : {
            key       = "${environment}-${role}-${object_id}"
            scope     = scope
            role      = role
            object_id = object_id
          }
        ]
      ]
    ]) : pair.key => pair
  }

  engineer_operations_roles = {
    for pair in flatten([
      for role in module.permissions.engineers_roles.operations : [
        for object_id in module.permissions.engineers_object_ids : {
          key       = "${role}-${object_id}"
          role      = role
          object_id = object_id
        }
      ]
    ]) : pair.key => pair
  }

  github_actions_environment_roles = {
    for pair in flatten([
      for environment, scope in local.environment_scopes : [
        for role in concat(
          module.permissions.github_actions_roles.host,
          environment == "feature" ? module.permissions.github_actions_roles.feature_only : [],
          ) : {
          key   = "${environment}-${role}"
          scope = scope
          role  = role
        }
      ]
    ]) : pair.key => pair
  }
}

resource "azurerm_role_assignment" "engineers-environment" {
  for_each = local.engineer_environment_roles

  scope                = each.value.scope
  role_definition_name = each.value.role
  principal_id         = each.value.object_id
  principal_type       = "User"
}

resource "azurerm_role_assignment" "engineers-operations" {
  for_each = local.engineer_operations_roles

  scope                = data.azurerm_resource_group.operations.id
  role_definition_name = each.value.role
  principal_id         = each.value.object_id
  principal_type       = "User"
}

resource "azurerm_cosmosdb_sql_role_assignment" "engineers-feature-data" {
  for_each = toset(module.permissions.engineers_object_ids)

  resource_group_name = azurerm_resource_group.feature.name
  account_name        = azurerm_cosmosdb_account.feature.name
  role_definition_id  = "${azurerm_cosmosdb_account.feature.id}/sqlRoleDefinitions/${module.permissions.cosmos_data_roles.contributor}"
  principal_id        = each.value
  scope               = azurerm_cosmosdb_account.feature.id
}

module "github-actions-federation" {
  source = "../../modules/github-federation"

  display_name = "GitHub Actions CI"
  description  = "Federated identity used by GitHub Actions to build, push, and deploy."
  subjects = [
    "repo:${var.github_repo}:ref:refs/heads/main",
    "repo:${var.github_repo}:pull_request",
    "repo:${var.github_repo}:environment:production",
  ]
  role_assignments = concat(
    [for role in module.permissions.github_actions_roles.operations : {
      role  = role
      scope = data.azurerm_resource_group.operations.id
    }],
    [for assignment in values(local.github_actions_environment_roles) : {
      role  = assignment.role
      scope = assignment.scope
    }],
  )
}

module "terraform-federation" {
  source = "../../modules/github-federation"

  display_name = "Terraform"
  description  = "Federated identity used by GitHub Actions and engineers to apply Terraform."
  subjects = [
    "repo:${var.github_repo}:ref:refs/heads/main",
    "repo:${var.github_repo}:environment:production",
  ]
  role_assignments = [
    {
      role  = "Owner"
      scope = local.subscription_scope
    },
  ]
}

resource "azurerm_cosmosdb_sql_role_assignment" "github-actions-feature-data" {
  resource_group_name = azurerm_resource_group.feature.name
  account_name        = azurerm_cosmosdb_account.feature.name
  role_definition_id  = "${azurerm_cosmosdb_account.feature.id}/sqlRoleDefinitions/${module.permissions.cosmos_data_roles.contributor}"
  principal_id        = module.github-actions-federation.service_principal_object_id
  scope               = azurerm_cosmosdb_account.feature.id
}

output "github_actions_client_id" {
  value = module.github-actions-federation.client_id
}

output "github_actions_service_principal_object_id" {
  value = module.github-actions-federation.service_principal_object_id
}

output "terraform_client_id" {
  value = module.terraform-federation.client_id
}

output "terraform_service_principal_object_id" {
  value = module.terraform-federation.service_principal_object_id
}
