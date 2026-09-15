resource "azurerm_role_assignment" "blob-data-contributor" {
  for_each = toset(var.principal_ids)

  scope                = azurerm_storage_container.container.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = each.value
  principal_type       = "ServicePrincipal"
}

resource "azurerm_role_assignment" "blob-data-reader" {
  for_each = toset(var.reader_principal_ids)

  scope                = azurerm_storage_container.container.id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = each.value
  principal_type       = "ServicePrincipal"
}
