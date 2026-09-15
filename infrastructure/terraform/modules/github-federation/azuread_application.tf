resource "azuread_application" "application" {
  display_name     = var.display_name
  description      = var.description
  owners           = var.owner_object_ids
  sign_in_audience = "AzureADMyOrg"
}
