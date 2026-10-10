variable "resource_group_name" {
  type        = string
  description = "Name of the resource group the job belongs to."
}

variable "location" {
  type        = string
  description = "Region the job is deployed to."
}

variable "container_app_environment_id" {
  type        = string
  description = "Resource ID of the Container App Environment that hosts the job."
}

variable "feature_environment" {
  type        = string
  description = "The environment-specific prefix to use when naming resources."
}

variable "service_name" {
  type        = string
  description = "The name of the service the job belongs to."
}

variable "job_name" {
  type        = string
  description = "The name of the job."
}

variable "parallelism" {
  type        = number
  description = "The number of replicas that run in parallel for one execution."
  default     = 1
}

variable "task_count" {
  type        = number
  description = "The number of replicas that must complete for an execution to be considered successful."
  default     = 1
}

variable "max_retries" {
  type        = number
  description = "The number of times a failed replica is retried."
  default     = 0
}

variable "task_timeout_seconds" {
  type        = number
  description = "The maximum time a replica is allowed to run before it is terminated."
  default     = 600
}

variable "identity_id" {
  type        = string
  description = "Resource ID of the user-assigned managed identity the job runs as."
}

variable "registry_login_server" {
  type        = string
  description = "Login server of the container registry the image is pulled from."
}

variable "image" {
  type        = string
  description = "Fully qualified container image to run. The default is a placeholder that lets the app be created before the first image is pushed; thereafter the deployment scripts own the image and Terraform ignores changes to it."
  default     = "mcr.microsoft.com/k8se/quickstart:latest"
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

variable "secret_env" {
  type        = map(string)
  description = "Environment variables whose values are read from Key Vault at runtime, as a map of variable name to versionless Key Vault secret URI. Values never enter Terraform state."
  default     = {}
}

variable "cpu" {
  type        = number
  description = "Number of vCPUs to allocate to each replica. Container Apps requires memory to be exactly twice this value in gibibytes."
  default     = 0.5
}

variable "memory" {
  type        = string
  description = "Amount of memory to allocate to each replica, as a Kubernetes quantity such as 1Gi."
  default     = "1Gi"
}

variable "schedule" {
  type        = string
  description = "The cron schedule for the job, interpreted in UTC. Empty leaves the job manually triggered."
  default     = ""
}

variable "tags" {
  type        = map(string)
  description = "Tags applied to the job."
  default     = {}
}
