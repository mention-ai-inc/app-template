resource "azuread_application_federated_identity_credential" "subjects" {
  for_each = toset(var.subjects)

  application_id = azuread_application.application.id
  display_name   = substr(replace(each.value, "/[^a-zA-Z0-9]/", "-"), 0, 120)
  description    = var.description
  audiences      = ["api://AzureADTokenExchange"]
  issuer         = var.issuer
  subject        = each.value
}
