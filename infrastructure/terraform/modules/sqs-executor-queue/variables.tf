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

variable "task_concurrency" {
  type        = number
  description = "Maximum number of commands the executor pool processes from this queue at once. Held as a queue attribute so the pool can size its own reader."
  default     = 80
}

variable "max_task_attempts" {
  type        = number
  description = "Maximum number of times a command is delivered before it moves to the dead-letter queue."
  default     = 5
}

variable "visibility_timeout_seconds" {
  type        = number
  description = "Seconds a received command is hidden from other readers. Must exceed the executor's own timeout."
  default     = 300
}

variable "message_retention_seconds" {
  type        = number
  description = "Seconds an unprocessed command stays on the queue before SQS discards it."
  default     = 345600
}

variable "dead_letter_retention_seconds" {
  type        = number
  description = "Seconds a dead-lettered command is kept for inspection."
  default     = 1209600
}

variable "reader_writer_role_arns" {
  type        = list(string)
  description = "IAM roles allowed to send to and receive from the queue."
  default     = []
}
