output "lease_container_name" {
  description = "Name of the lease container the change feed processor checkpoints into."
  value       = azurerm_cosmosdb_sql_container.leases.name
}

output "routing" {
  description = "What the trigger pool needs to run this trigger: the container it reads, the leases it checkpoints into, and the documentType it acts on."
  value = {
    trigger_name         = var.trigger_name
    container_name       = var.watched_container_name
    lease_container_name = azurerm_cosmosdb_sql_container.leases.name
    document_type        = var.document_type
  }
}
