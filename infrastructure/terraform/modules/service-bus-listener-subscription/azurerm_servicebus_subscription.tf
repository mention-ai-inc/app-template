locals {
  capped_lock_duration_seconds = min(var.timeout_seconds, 300)
  lock_duration                = local.capped_lock_duration_seconds % 60 == 0 ? "PT${floor(local.capped_lock_duration_seconds / 60)}M" : "PT${local.capped_lock_duration_seconds}S"

  indexed_subscriptions = { for index, subscription in var.subscriptions : index => subscription }
}

resource "azurerm_servicebus_subscription" "listener" {
  for_each = local.indexed_subscriptions

  name     = join("", [var.feature_environment, var.service_name, "-", replace(var.listener_name, "_", "-"), "-", each.key])
  topic_id = "${var.namespace_id}/topics/${var.feature_environment}${each.value.topic_name}"

  max_delivery_count                        = var.max_delivery_attempts
  lock_duration                             = local.lock_duration
  dead_lettering_on_message_expiration      = true
  dead_lettering_on_filter_evaluation_error = true
  batched_operations_enabled                = true
}
