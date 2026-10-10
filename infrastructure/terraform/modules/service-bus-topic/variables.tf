variable "namespace_id" {
  type        = string
  description = "Resource ID of the Service Bus namespace the topic is created in."
}

variable "feature_environment" {
  type        = string
  description = "The environment-specific prefix to use when naming resources."
}

variable "topic_name" {
  type        = string
  description = "Name of the topic, which every listener subscribes to by name."
}

variable "message_ttl" {
  type        = string
  description = "ISO 8601 duration after which an undelivered message expires."
  default     = "P14D"
}

variable "archive" {
  type        = bool
  description = "Whether to create a durable subscription that retains every message for the archiver to drain into blob storage."
  default     = false
}

variable "archive_max_delivery_count" {
  type        = number
  description = "Number of deliveries before an archive message is moved to the archive subscription's dead-letter sub-queue."
  default     = 10
}
