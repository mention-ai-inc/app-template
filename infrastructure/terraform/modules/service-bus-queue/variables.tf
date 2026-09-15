variable "namespace_id" {
  type        = string
  description = "Resource ID of the Service Bus namespace the queue is created in."
}

variable "feature_environment" {
  type        = string
  description = "The environment-specific prefix to use when naming resources."
}

variable "service_name" {
  type        = string
  description = "Name of the service that owns the command."
}

variable "command_name" {
  type        = string
  description = "Name of the command, which is used in the name of the queue."
}

variable "max_task_attempts" {
  type        = number
  description = "Number of deliveries before a message is moved to the queue's dead-letter sub-queue."
  default     = 5
}

variable "lock_duration_seconds" {
  type        = number
  description = "How long a received message stays invisible to other receivers before it is redelivered. Service Bus caps this at 300 seconds; longer work must renew the lock."
  default     = 300
}

variable "message_ttl" {
  type        = string
  description = "ISO 8601 duration after which an undelivered message expires and is dead-lettered."
  default     = "P14D"
}

variable "max_size_in_megabytes" {
  type        = number
  description = "Maximum size of the queue."
  default     = 1024
}
