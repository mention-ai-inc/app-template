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
  description = "Name of the listener, which names its queues and selects its handler within the listener pool."
}

variable "subscriptions" {
  type = list(object({
    event_name          = string
    source_service_name = string
    topic_name          = string
    model_name          = optional(string)
  }))
  description = "List of subscription configurations. Each one creates its own queue on the named topic, filtered to the named events, all feeding the same listener."
}

variable "topic_arns" {
  type        = map(string)
  description = "ARNs of every event topic, keyed by the topic name used in the subscriptions."
}

variable "timeout_seconds" {
  type        = number
  description = "Seconds a received event is hidden from other readers. Must exceed the listener's own timeout."
  default     = 60
}

variable "max_delivery_attempts" {
  type        = number
  description = "Number of delivery attempts before an event is moved to the dead-letter queue."
  default     = 5
}

variable "message_retention_seconds" {
  type        = number
  description = "Seconds an unprocessed event stays on the queue before SQS discards it."
  default     = 345600
}

variable "dead_letter_retention_seconds" {
  type        = number
  description = "Seconds a dead-lettered event is kept for inspection."
  default     = 1209600
}

variable "reader_role_arns" {
  type        = list(string)
  description = "IAM roles allowed to receive from the listener's queues."
  default     = []
}
