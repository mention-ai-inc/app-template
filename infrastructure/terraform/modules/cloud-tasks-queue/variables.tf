# admin
variable "project_id" {
  type        = string
  description = "ID of the GCP project the service belongs to."
}

variable "region" {
  type        = string
  description = "Region where the queue will be created. Used when a resource asks for region or location."
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

# cloud tasks configuration
variable "task_concurrency" {
  type        = number
  description = "Maximum number of concurrent tasks dispatched by the queue."
  default     = 80
}

variable "max_tasks_per_second" {
  type        = number
  description = "Maximum number of tasks per second dispatched by the queue."
  default     = 50
}

variable "max_task_attempts" {
  type        = number
  description = "Maximum number of times a task will be retried."
  default     = 5
}

variable "minimum_backoff_seconds" {
  type        = number
  description = "Minimum amount of time to wait before retrying a task after it fails."
  default     = 5
}

variable "maximum_backoff_seconds" {
  type        = number
  description = "Maximum amount of time to wait before retrying a task after it fails."
  default     = 3600
}

variable "maximum_doublings" {
  type        = number
  description = "Maximum number of times that the interval between failed task retries will be doubled before the increase becomes constant."
  default     = 16
}
