output "client_id" {
  description = "Application ID that a workflow passes to azure/login as client-id."
  value       = azuread_application.application.client_id
}

output "object_id" {
  description = "Object ID of the application registration."
  value       = azuread_application.application.object_id
}

output "service_principal_object_id" {
  description = "Object ID of the service principal, which is what role assignments grant to."
  value       = azuread_service_principal.application.object_id
}
