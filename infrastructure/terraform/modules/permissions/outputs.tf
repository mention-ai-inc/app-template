output "engineers_members" {
  value = local.engineers.members
}

output "engineers_service_actions" {
  value = local.engineers.service_actions
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
