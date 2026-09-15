output "topic_id" {
  description = "Resource ID of the topic."
  value       = azurerm_servicebus_topic.topic.id
}

output "topic_name" {
  description = "Name of the topic, including the feature environment prefix."
  value       = azurerm_servicebus_topic.topic.name
}

output "archive_subscription_name" {
  description = "Name of the archive subscription, empty when the topic is not archived."
  value       = var.archive ? azurerm_servicebus_subscription.archive[0].name : ""
}
