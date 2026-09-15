output "container_app_name" {
  description = "The name of the deployed Container App."
  value       = azurerm_container_app.pool.name
}
