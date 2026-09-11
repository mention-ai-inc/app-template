# admin
variable "project_id" {
  type        = string
  description = "ID of the GCP project the service belongs to."
}

variable "region" {
  type        = string
  description = "Region where the service will be deployed. Used when a resource asks for region or location."
}

variable "feature_environment" {
  type        = string
  description = "The environment-specific prefix to use when naming resources. Supplied in order to inject it into the environment for Cloud Run services, so that resources can be correctly accessed in application code."
}

variable "service_name" {
  type        = string
  description = "Name of the service the command handler belongs to."
}

# cloud tasks configuration
variable "command_name" {
  type        = string
  description = "Name of the command, which is used in the name of the queue."
}

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

# cloud run configuration
variable "service_account_email" {
  type        = string
  description = "Email address of the service account to associate with the service."
}

variable "image_uri" {
  type        = string
  description = "URI of the container image to deploy."
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "command" {
  type        = list(string)
  description = "The command to pass to the container."
  default     = null
}

variable "container_concurrency" {
  type        = number
  description = "Maximum number of concurrent requests allowed for a container."
  default     = 80
}

variable "timeout_seconds" {
  type        = number
  description = "Maximum number of seconds a request can take before the request is cancelled."
  default     = 60
}

variable "minimum_instances" {
  type        = number
  description = "Minimum number of container instances to run."
  default     = 0
}

variable "maximum_instances" {
  type        = number
  description = "Maximum number of container instances to run."
  default     = 10
}

variable "cpu" {
  type        = string
  description = "Number of vCPUs to allocate to the service, as a string."
  default     = "1"
}

variable "memory" {
  type        = string
  description = "Amount of memory to allocate to the service, in MB. For example, 256Mi = 256 MB."
  default     = "512Mi"
}

variable "env" {
  type        = map(string)
  description = "Environment variables to set in the container."
  default     = {}
}

# networking
variable "vpc_network" {
  type        = string
  description = "The ID of the VPC network to deploy the service to."
  default     = ""
}

variable "vpc_subnetwork" {
  type        = string
  description = "The ID of the VPC subnet to deploy the service to."
  default     = ""
}

# scheduler
variable "health_check_interval_minutes" {
  type        = number
  description = "Interval between health checks, in minutes."
  default     = 15
}
