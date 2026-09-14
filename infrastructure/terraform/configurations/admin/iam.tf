module "permissions" {
  source = "../../modules/permissions"

  services = []
}

locals {
  admin_impersonation_roles = local.is_production ? [
    "roles/iam.serviceAccountTokenCreator",
    ] : [
    "roles/iam.serviceAccountUser",
    "roles/iam.serviceAccountTokenCreator",
  ]
  admin_impersonation_bindings = {
    for pair in setproduct(
      keys(data.terraform_remote_state.services.outputs.service_account_uris),
      local.admin_impersonation_roles,
      ) : "${pair[0]}-${pair[1]}" => {
      account_uri = data.terraform_remote_state.services.outputs.service_account_uris[pair[0]]
      role        = pair[1]
    }
  }
}

resource "google_service_account_iam_member" "admin-service-impersonation" {
  for_each = local.admin_impersonation_bindings

  service_account_id = each.value.account_uri
  role               = each.value.role
  member             = "serviceAccount:${module.admin-service-account.email}"
}
