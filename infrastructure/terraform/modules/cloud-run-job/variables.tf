# admin
variable "project_id" {
  description = "The ID of the project in which the resource belongs."
  type        = string
}

variable "project_number" {
  description = "The number of the project in which the resource belongs."
  type        = string
}

variable "region" {
  description = "The region in which the resource should be deployed."
  type        = string
}

variable "feature_environment" {
  type        = string
  description = "The environment-specific prefix to use when naming resources."
}

variable "service_name" {
  description = "The name of the service the job belongs to."
  type        = string
  default     = null
}

variable "job_name" {
  description = "The name of the job."
  type        = string
}

# job execution
variable "parallelism" {
  description = "The number of jobs executions that can run in parallel."
  type        = number
  default     = 1
}

variable "task_count" {
  description = "The number of tasks to run."
  type        = number
  default     = 1
}

variable "max_retries" {
  description = "The number of times to retry the task."
  type        = number
  default     = 0
}

variable "task_timeout" {
  description = "The maximum time a task is allowed to run before it is terminated."
  type        = string
  default     = "600s"
}

variable "service_account_email" {
  description = "The email of the service account to use for the task."
  type        = string
}

variable "image_uri" {
  description = "The docker image to use for the task."
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/job:latest"
}

variable "command" {
  type        = list(string)
  description = "The command to pass to the container."
  default     = null
}

variable "env" {
  type        = map(string)
  description = "Environment variables to set in the container."
  default     = {}
}

# hardware
variable "cpu" {
  type        = string
  description = "Number of vCPUs to allocate to each execution, as a string."
  default     = "1"
}

variable "memory" {
  type        = string
  description = "Amount of memory to allocate to the service, in MB. For example, 256Mi = 256 MB."
  default     = "512Mi"
}

variable "gpus" {
  type        = string
  description = "Number of GPUs to allocate to each execution. Set to '0' or leave empty for no GPU."
  default     = "0"
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

# scheduling
variable "schedule" {
  description = "The cron schedule for the job."
  type        = string
  default     = ""
}
