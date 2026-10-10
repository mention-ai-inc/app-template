output "container_name" {
  description = "The name of the container."
  value       = azurerm_storage_container.container.name
}

output "resource_manager_id" {
  description = "The Azure Resource Manager ID of the container, which is the scope a data-plane role assignment is made at."
  value       = azurerm_storage_container.container.id
}
