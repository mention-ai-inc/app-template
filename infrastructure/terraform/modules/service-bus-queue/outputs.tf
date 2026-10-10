output "queue_name" {
  description = "The name of the Service Bus queue created for this command."
  value       = azurerm_servicebus_queue.queue.name
}
