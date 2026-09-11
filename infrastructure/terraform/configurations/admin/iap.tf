locals {
  iap_oauth_client_id = data.google_secret_manager_secret_version_access.iap-oauth-client-id.secret_data
  iap_accessors = concat(
    [for engineer in module.permissions.engineers_members : "user:${engineer}"],
    local.is_production ? [] : ["serviceAccount:terraform@acme-operations-155d.iam.gserviceaccount.com"],
  )
}

resource "google_iap_settings" "admin" {
  name = "projects/${local.project}/iap_web/compute/services/${module.admin-server.backend_service_name}"

  access_settings {
    oauth_settings {
      client_id     = local.iap_oauth_client_id
      client_secret = data.google_secret_manager_secret_version_access.iap-oauth-client-secret.secret_data
      programmatic_clients = [
        local.iap_oauth_client_id,
      ]
    }
  }
}

resource "google_iap_web_backend_service_iam_member" "admin-accessors" {
  for_each = toset(local.iap_accessors)

  project             = local.project
  web_backend_service = module.admin-server.backend_service_name
  role                = "roles/iap.httpsResourceAccessor"
  member              = each.value
}

output "iap_client_id" {
  description = "OAuth client ID of the IAP client, used as the audience when minting service-account ID tokens for programmatic access."
  value       = local.iap_oauth_client_id
  sensitive   = true
}
