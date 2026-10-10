variable "resource_group_name" {
  type        = string
  description = "Name of the resource group the Container App belongs to."
}

variable "container_app_environment_id" {
  type        = string
  description = "Resource ID of the Container App Environment that hosts the pool."
}

variable "feature_environment" {
  type        = string
  description = "The environment-specific prefix to use when naming resources. Supplied in order to inject it into the environment for Container Apps, so that resources can be correctly accessed in application code."
}

variable "service_name" {
  type        = string
  description = "Name of the service whose entrypoints the pool hosts."
}

variable "pool_name" {
  type        = string
  description = "Name of the pool, which distinguishes it from the other pools of the same service and appears in its Container App name."
}

variable "component_type" {
  type        = string
  description = "The kind of entrypoint the pool hosts. Every entrypoint in one pool is of the same kind, so this stays a per-process constant."

  validation {
    condition     = contains(["executor", "listener", "trigger"], var.component_type)
    error_message = "A pool hosts executors, listeners, or triggers."
  }
}

variable "identity_id" {
  type        = string
  description = "Resource ID of the user-assigned managed identity the pool runs as, pulls images as, reads Key Vault secrets as, and authenticates its scale rules with."
}

variable "registry_login_server" {
  type        = string
  description = "Login server of the container registry the image is pulled from."
}

variable "image" {
  type        = string
  description = "Fully qualified container image to deploy. The default is a placeholder that lets the app be created before the first image is pushed; thereafter the deployment scripts own the image and Terraform ignores changes to it."
  default     = "mcr.microsoft.com/k8se/quickstart:latest"
}

variable "command" {
  type        = list(string)
  description = "The command to pass to the container."
  default     = null
}

variable "minimum_instances" {
  type        = number
  description = "Minimum number of replicas to run. Trigger pools set this to at least one because the change feed processor is a long-running consumer rather than a request handler."
  default     = 0
}

variable "maximum_instances" {
  type        = number
  description = "Maximum number of replicas to run."
  default     = 10
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

variable "service_bus_namespace_name" {
  type        = string
  description = "Short name of the Service Bus namespace the scale rules poll. KEDA takes the name rather than the hostname when it authenticates with a managed identity."
  default     = ""
}

variable "queue_scale_rules" {
  type = list(object({
    name          = string
    queue_name    = string
    message_count = optional(number, 5)
  }))
  description = "Service Bus queues whose backlog scales the pool. Used by executor pools, one rule per command queue."
  default     = []
}

variable "subscription_scale_rules" {
  type = list(object({
    name              = string
    topic_name        = string
    subscription_name = string
    message_count     = optional(number, 5)
  }))
  description = "Service Bus topic subscriptions whose backlog scales the pool. Used by listener pools, one rule per subscription."
  default     = []
}

variable "tags" {
  type        = map(string)
  description = "Tags applied to the Container App."
  default     = {}
}
