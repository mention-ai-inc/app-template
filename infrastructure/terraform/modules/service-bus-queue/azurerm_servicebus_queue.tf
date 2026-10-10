locals {
  capped_lock_duration_seconds = min(var.lock_duration_seconds, 300)
  lock_duration                = local.capped_lock_duration_seconds % 60 == 0 ? "PT${floor(local.capped_lock_duration_seconds / 60)}M" : "PT${local.capped_lock_duration_seconds}S"
}

resource "azurerm_servicebus_queue" "queue" {
  name         = join("", [var.feature_environment, var.service_name, "-", replace(var.command_name, "_", "-")])
  namespace_id = var.namespace_id

  lock_duration                        = local.lock_duration
  max_delivery_count                   = var.max_task_attempts
  default_message_ttl                  = var.message_ttl
  max_size_in_megabytes                = var.max_size_in_megabytes
  dead_lettering_on_message_expiration = true
  batched_operations_enabled           = true
}
