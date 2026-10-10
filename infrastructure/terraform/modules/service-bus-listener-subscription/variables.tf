variable "namespace_id" {
  type        = string
  description = "Resource ID of the Service Bus namespace that holds the topics the listener subscribes to."
}

variable "feature_environment" {
  type        = string
  description = "The environment-specific prefix to use when naming resources."
}

variable "service_name" {
  type        = string
  description = "Name of the service that owns the listener."
}

variable "listener_name" {
  type        = string
  description = "Name of the listener, which names the subscriptions and selects its route within the listener pool."
}

variable "subscriptions" {
  type = list(object({
    event_name          = string
    source_service_name = string
    topic_name          = string
    model_name          = optional(string)
  }))
  description = "List of subscription configurations. Each one creates a separate Service Bus subscription that the listener pool drains."
}

variable "timeout_seconds" {
  type        = number
  description = "How long a received message stays invisible to other receivers before it is redelivered. Service Bus caps this at 300 seconds."
  default     = 60
}

variable "max_delivery_attempts" {
  type        = number
  description = "Number of deliveries before a message is moved to the subscription's dead-letter sub-queue."
  default     = 5
}
