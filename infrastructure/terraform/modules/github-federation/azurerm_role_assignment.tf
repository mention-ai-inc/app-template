resource "azurerm_role_assignment" "assigned-roles" {
  for_each = var.role_assignments

  scope                = each.value.scope
  role_definition_name = each.value.role
  principal_id         = azuread_service_principal.application.object_id
  principal_type       = "ServicePrincipal"
}
