resource "azurerm_servicebus_subscription" "archive" {
  count = var.archive ? 1 : 0

  name     = join("", [var.feature_environment, var.topic_name, "-archive"])
  topic_id = azurerm_servicebus_topic.topic.id

  max_delivery_count                   = var.archive_max_delivery_count
  default_message_ttl                  = var.message_ttl
  dead_lettering_on_message_expiration = true
}
