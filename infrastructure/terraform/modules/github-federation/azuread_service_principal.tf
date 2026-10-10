resource "azuread_service_principal" "application" {
  client_id                    = azuread_application.application.client_id
  app_role_assignment_required = false
  owners                       = var.owner_object_ids
  description                  = var.description
}
