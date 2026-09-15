output "id" {
  description = "Resource ID of the identity, which is what a Container App references to run as it."
  value       = azurerm_user_assigned_identity.identity.id
}

output "principal_id" {
  description = "Object ID of the identity's service principal, which is what a role assignment grants to."
  value       = azurerm_user_assigned_identity.identity.principal_id
}

output "client_id" {
  description = "Application ID of the identity, which is what the Azure SDKs use to select it inside a multi-identity workload."
  value       = azurerm_user_assigned_identity.identity.client_id
}

output "name" {
  description = "Name of the identity."
  value       = azurerm_user_assigned_identity.identity.name
}
