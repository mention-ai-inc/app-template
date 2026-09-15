locals {
  staff_allowlist = module.permissions.engineers_members
}

resource "azuread_application" "admin" {
  display_name     = "${local.feature_environment}Acme Admin"
  description      = "Entra ID application the admin API validates its callers against."
  sign_in_audience = "AzureADMyOrg"

  web {
    redirect_uris = ["https://${local.admin_fqdn}/auth/callback"]

    implicit_grant {
      id_token_issuance_enabled = false
    }
  }

  api {
    requested_access_token_version = 2
  }
}

resource "azuread_service_principal" "admin" {
  client_id                    = azuread_application.admin.client_id
  app_role_assignment_required = true
  description                  = "Entra ID service principal for the admin API."
}

output "admin_client_id" {
  description = "Application ID callers request an access token for, used as the audience the admin API validates."
  value       = azuread_application.admin.client_id
}
