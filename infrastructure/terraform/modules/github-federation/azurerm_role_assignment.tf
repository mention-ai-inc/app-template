resource "azurerm_role_assignment" "assigned-roles" {
  for_each = { for assignment in var.role_assignments : "${assignment.scope}|${assignment.role}" => assignment }

  scope                = each.value.scope
  role_definition_name = each.value.role
  principal_id         = azuread_service_principal.application.object_id
  principal_type       = "ServicePrincipal"
}
