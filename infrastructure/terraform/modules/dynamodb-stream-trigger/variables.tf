variable "feature_environment" {
  type        = string
  description = "The environment-specific prefix to use when naming resources."
}

variable "service_name" {
  type        = string
  description = "Name of the service that owns the trigger."
}

variable "trigger_name" {
  type        = string
  description = "Name of the trigger, which names its queue and selects its handler within the trigger pool."
}

variable "collection" {
  type        = string
  description = "The service-owned collection whose items the trigger matches. Partition keys are prefixed with the feature environment, the service, and the collection."
}

variable "table_stream_arn" {
  type        = string
  description = "ARN of the document store's change stream."
}

variable "batch_size" {
  type        = number
  description = "Maximum number of stream records the pipe puts on the queue in one batch."
  default     = 10
}

variable "maximum_batching_window_seconds" {
  type        = number
  description = "Seconds the pipe waits to fill a batch before delivering a partial one."
  default     = 5
}

variable "maximum_retry_attempts" {
  type        = number
  description = "Times the pipe retries a batch before discarding it."
  default     = 5
}

variable "parallelization_factor" {
  type        = number
  description = "Concurrent batches the pipe reads from a single shard."
  default     = 1
}

variable "timeout_seconds" {
  type        = number
  description = "Seconds a received record is hidden from other readers. Must exceed the trigger's own timeout."
  default     = 60
}

variable "message_retention_seconds" {
  type        = number
  description = "Seconds an unprocessed record stays on the queue before SQS discards it."
  default     = 345600
}

variable "dead_letter_retention_seconds" {
  type        = number
  description = "Seconds a dead-lettered record is kept for inspection."
  default     = 1209600
}

variable "max_delivery_attempts" {
  type        = number
  description = "Number of delivery attempts before a record is moved to the dead-letter queue."
  default     = 5
}

variable "reader_role_arns" {
  type        = list(string)
  description = "IAM roles allowed to receive from the trigger's queue."
  default     = []
}
