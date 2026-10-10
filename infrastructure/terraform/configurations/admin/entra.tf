locals {
  staff_allowlist = module.permissions.engineers_members

  auth_client_secret_variable     = "MICROSOFT_PROVIDER_AUTHENTICATION_SECRET"
  auth_client_secret_setting_name = lower(replace(local.auth_client_secret_variable, "_", "-"))
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

resource "azuread_application_password" "admin" {
  application_id = azuread_application.admin.id
  display_name   = "container-app-built-in-auth"
}

resource "azurerm_key_vault_secret" "admin-auth-client-secret" {
  name         = "${local.feature_environment}ADMIN-AUTH-CLIENT-SECRET"
  value        = azuread_application_password.admin.value
  key_vault_id = local.key_vault_id
}

resource "azapi_resource" "admin-built-in-auth" {
  type      = "Microsoft.App/containerApps/authConfigs@2024-03-01"
  name      = "current"
  parent_id = module.admin-server.container_app_id

  body = {
    properties = {
      platform = {
        enabled = true
      }

      globalValidation = {
        unauthenticatedClientAction = "RedirectToLoginPage"
        redirectToProvider          = "azureactivedirectory"
      }

      identityProviders = {
        azureActiveDirectory = {
          enabled = true

          registration = {
            openIdIssuer            = "https://login.microsoftonline.com/${var.tenant_id}/v2.0"
            clientId                = azuread_application.admin.client_id
            clientSecretSettingName = local.auth_client_secret_setting_name
          }

          validation = {
            allowedAudiences = [azuread_application.admin.client_id]
          }
        }
      }

      login = {
        tokenStore = {
          enabled = true
        }
      }
    }
  }
}
