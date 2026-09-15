output "engineers_members" {
  value = local.engineers.members
}

output "engineers_policy_arns" {
  value = {
    production = local.engineers.policy_arns.host,
    feature    = concat(local.engineers.policy_arns.host, local.engineers.policy_arns.feature_only)
    operations = local.engineers.policy_arns.operations
  }
}

output "service_actions" {
  value = {
    host = {
      for service in var.services : service => concat(local.services_permissions.common_actions.host, lookup(local.services_permissions.individual_actions, service, { host = [] }).host)
    },
    operations = {
      for service in var.services : service => concat(local.services_permissions.common_actions.operations, lookup(local.services_permissions.individual_actions, service, { operations = [] }).operations)
    }
  }
}

output "github_actions_actions" {
  value = {
    host         = local.github_actions.actions.host,
    feature_only = local.github_actions.actions.feature_only,
    operations   = local.github_actions.actions.operations
  }
}
