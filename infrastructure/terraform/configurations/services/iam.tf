# permissions
module "permissions" {
  source = "../../modules/permissions"

  services = keys(var.services)
}

# service accounts
module "service-service-account" {
  source   = "../../modules/service-account"
  for_each = toset(keys(var.services))

  project_id         = local.project
  account_id         = "${local.feature_environment}${each.value}-s"
  roles              = lookup(module.permissions.service_roles.host, each.value, [])
  user_impersonaters = local.is_production ? [] : module.permissions.engineers_members
}

# grant service account permissions in the operations project
resource "google_project_iam_member" "service-operations-permissions" {
  for_each = {
    for pair in flatten([
      for service in keys(var.services) : [
        for role in lookup(module.permissions.service_roles.operations, service, []) : {
          service = service
          role    = role
          key     = "${service}-${role}"
        }
      ]
    ]) : pair.key => pair
  }

  project = var.operations_project_id
  role    = each.value.role
  member  = "serviceAccount:${module.service-service-account[each.value.service].email}"
}

# Cross-service-account impersonation permissions
# This allows each service account to impersonate all other service accounts
resource "google_service_account_iam_member" "cross-service-impersonation" {
  for_each = {
    for pair in flatten([
      for service_a in keys(var.services) : [
        for service_b in keys(var.services) : {
          target_service       = service_a
          impersonator_service = service_b
          key                  = "${service_a}-impersonated-by-${service_b}"
        }
        if service_a != service_b # Don't allow self-impersonation (already handled by module)
      ]
    ]) : pair.key => pair
  }

  service_account_id = module.service-service-account[each.value.target_service].account_uri
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${module.service-service-account[each.value.impersonator_service].email}"
}

module "persistence-service-account" {
  # used by compute engine instances running self-hosted databases

  source = "../../modules/service-account"

  project_id = local.project
  account_id = "${local.feature_environment}persistence"
  roles = [
    "roles/monitoring.metricWriter",
    "roles/logging.logWriter",
  ]
}

resource "google_project_iam_member" "persistence-operations-permissions" {
  project = var.operations_project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${module.persistence-service-account.email}"
}

module "default-service-account" {
  source = "../../modules/service-account"

  project_id = local.project
  account_id = "${local.feature_environment}default"
  roles = [
    "roles/viewer",
  ]
}

module "cloud-build-service-account" {
  source = "../../modules/service-account"

  project_id = local.project
  account_id = "${local.feature_environment}cloud-build"
  roles = [
    "roles/artifactregistry.writer",
    "roles/logging.logWriter",
    "roles/storage.objectAdmin",
  ]
}

resource "google_project_iam_member" "cloud-build-operations-permissions" {
  project = var.operations_project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${module.cloud-build-service-account.email}"
}
