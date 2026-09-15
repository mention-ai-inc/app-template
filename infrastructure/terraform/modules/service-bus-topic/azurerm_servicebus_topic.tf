resource "azurerm_servicebus_topic" "topic" {
  name         = join("", [var.feature_environment, var.topic_name])
  namespace_id = var.namespace_id

  default_message_ttl        = var.message_ttl
  support_ordering           = true
  batched_operations_enabled = true
}
