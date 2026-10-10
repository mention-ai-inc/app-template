# permissions
module "permissions" {
  source = "../../modules/permissions"

  services = []
}

# users
resource "google_project_iam_member" "engineers-roles" {
  for_each = { for role_user_pair in flatten([
    for user in module.permissions.engineers_members : [
      for role in module.permissions.engineers_roles.operations : {
        role = role
        user = user
      }
    ]
  ]) : "${role_user_pair.role}-${role_user_pair.user}" => role_user_pair }

  project = var.operations_project_id
  member  = "user:${each.value.user}"
  role    = each.value.role
}

# service accounts
module "github-actions-service-account" {
  source = "../../modules/service-account"

  project_id = var.operations_project_id
  account_id = "github-actions"
  roles      = module.permissions.github_actions_roles.operations
}

# user
resource "google_project_iam_member" "production-engineers-roles" {
  for_each = { for role_user_pair in flatten([
    for user in module.permissions.engineers_members : [
      for role in module.permissions.engineers_roles.production : {
        role = role
        user = user
      }
    ]
  ]) : "${role_user_pair.role}-${role_user_pair.user}" => role_user_pair }

  project = module.production-project.project_id
  member  = "user:${each.value.user}"
  role    = each.value.role
}

resource "google_project_iam_member" "feature-engineers-roles" {
  for_each = { for role_user_pair in flatten([
    for user in module.permissions.engineers_members : [
      for role in module.permissions.engineers_roles.feature : {
        role = role
        user = user
      }
    ]
  ]) : "${role_user_pair.role}-${role_user_pair.user}" => role_user_pair }

  project = module.feature-project.project_id
  member  = "user:${each.value.user}"
  role    = each.value.role
}


# cross-project permissions
resource "google_project_iam_member" "production-github-actions-host-roles" {
  for_each = toset(module.permissions.github_actions_roles.host)

  project = module.production-project.project_id
  member  = "serviceAccount:${module.github-actions-service-account.email}"
  role    = each.value
}

resource "google_project_iam_member" "feature-github-actions-host-roles" {
  for_each = toset(module.permissions.github_actions_roles.host)

  project = module.feature-project.project_id
  member  = "serviceAccount:${module.github-actions-service-account.email}"
  role    = each.value
}

resource "google_project_iam_member" "feature-sign-jwt-roles" {
  for_each = {
    for pair in setproduct(
      [
        "serviceAccount:${module.github-actions-service-account.email}",
        "serviceAccount:${local.terraform_service_account}",
      ],
      toset(module.permissions.github_actions_roles.feature_only)
      ) : "${pair[0]}|${pair[1]}" => {
      member = pair[0]
      role   = pair[1]
    }
  }

  project = module.feature-project.project_id
  member  = each.value.member
  role    = each.value.role
}

resource "google_project_iam_member" "cloud-run-service-accounts" {
  for_each = { for service_account_role_pair in flatten([
    for service_account in keys(local.cloud_run_service_accounts) : [
      for role in local.cloud_run_roles : {
        service_account_key   = service_account
        service_account_email = local.cloud_run_service_accounts[service_account]
        role                  = role
      }
    ]
  ]) : "${service_account_role_pair.service_account_key}-${service_account_role_pair.role}" => service_account_role_pair }

  project = var.operations_project_id
  member  = "serviceAccount:${each.value.service_account_email}"
  role    = each.value.role
}

resource "google_service_account_iam_member" "terraform-self-token-creator" {
  service_account_id = "projects/${var.operations_project_id}/serviceAccounts/${local.terraform_service_account}"
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:${local.terraform_service_account}"
}

resource "google_project_iam_member" "pubsub-token-creator-production" {
  project = module.production-project.project_id
  member  = "serviceAccount:service-${module.production-project.project_number}@gcp-sa-pubsub.iam.gserviceaccount.com"
  role    = "roles/iam.serviceAccountTokenCreator"
}

resource "google_project_iam_member" "pubsub-token-creator-feature" {
  project = module.feature-project.project_id
  member  = "serviceAccount:service-${module.feature-project.project_number}@gcp-sa-pubsub.iam.gserviceaccount.com"
  role    = "roles/iam.serviceAccountTokenCreator"
}

# workload identity pools
module "github-actions-workload-identity" {
  source = "../../modules/workload-identity"

  project_id             = var.operations_project_id
  id                     = "github-actions-ci"
  display_name           = "GitHub Actions CI"
  pool_description       = "Workload Identity Federation pool for accessing the GitHub Actions service account."
  issuer_uri             = "https://token.actions.githubusercontent.com"
  member_attribute_name  = "repository"
  member_attribute_value = var.github_repo
  service_account_uris = [
    module.github-actions-service-account.account_uri
  ]
  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.aud"        = "assertion.aud"
    "attribute.actor"      = "assertion.actor"
    "attribute.repository" = "assertion.repository"
  }
  attribute_condition = "assertion.repository == \"${var.github_repo}\""
}

module "terraform-workload-identity" {
  source = "../../modules/workload-identity"

  project_id             = var.operations_project_id
  id                     = "terraform"
  display_name           = "Terraform"
  pool_description       = "Workload Identity Federation pool for accessing the Terraform service account."
  issuer_uri             = "https://token.actions.githubusercontent.com"
  member_attribute_name  = "repository"
  member_attribute_value = var.github_repo
  service_account_uris = [
    "projects/${var.operations_project_id}/serviceAccounts/${local.terraform_service_account}"
  ]
  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.aud"        = "assertion.aud"
    "attribute.actor"      = "assertion.actor"
    "attribute.repository" = "assertion.repository"
  }
  attribute_condition = "assertion.repository == \"${var.github_repo}\""
}

# google-managed service accounts granted additional roles
# https://cloud.google.com/run/docs/configuring/shared-vpc-direct-vpc#set_up_iam_permissions
locals {
  cloud_run_service_accounts = {
    "feature-serverless"       = "service-${module.feature-project.project_number}@serverless-robot-prod.iam.gserviceaccount.com",
    "production-serverless"    = "service-${module.production-project.project_number}@serverless-robot-prod.iam.gserviceaccount.com",
    "feature-cloudservices"    = "${module.feature-project.project_number}@cloudservices.gserviceaccount.com",
    "production-cloudservices" = "${module.production-project.project_number}@cloudservices.gserviceaccount.com"
  }
  cloud_run_roles = [
    "roles/compute.networkUser",
    "roles/compute.networkViewer",
    "roles/compute.networkAdmin"
  ]
}

# outputs
output "github-actions-service-account-uri" {
  value = module.github-actions-service-account.account_uri
}
output "github-actions-service-account-email" {
  value = module.github-actions-service-account.email
}
