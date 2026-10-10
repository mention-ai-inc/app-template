output "engineers_members" {
  value = local.engineers.members
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
