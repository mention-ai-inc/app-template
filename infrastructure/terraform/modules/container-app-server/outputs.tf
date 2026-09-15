output "service_name" {
  description = "The name of the service being deployed."
  value       = var.service_name
}

output "container_app_name" {
  description = "The name of the deployed Container App."
  value       = azurerm_container_app.server.name
}

output "fqdn" {
  description = "The hostname the managed ingress serves on within the environment's default domain."
  value       = azurerm_container_app.server.ingress[0].fqdn
}

output "custom_domain_fqdn" {
  description = "The custom hostname bound to the app, empty when none is configured."
  value       = var.custom_domain_fqdn
}

output "url" {
  description = "The base URL callers reach the server at, preferring the custom domain when one is bound."
  value       = local.has_custom_domain ? "https://${var.custom_domain_fqdn}" : "https://${azurerm_container_app.server.ingress[0].fqdn}"
}
