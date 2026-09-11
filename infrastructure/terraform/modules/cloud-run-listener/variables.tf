# admin
variable "project_id" {
  type        = string
  description = "ID of the GCP project the service belongs to."
}

variable "project_number" {
  type        = string
  description = "Number of the GCP project the service belongs to."
}

variable "region" {
  type        = string
  description = "Region where the service will be deployed. Used when a resource asks for region or location."
}

variable "feature_environment" {
  type        = string
  description = "The environment-specific prefix to use when naming resources. Supplied in order to inject it into the environment for Cloud Run services, so that resources can be correctly accessed in application code."
}

# pubsub
variable "subscriptions" {
  type = list(object({
    event_name          = string
    source_service_name = string
    topic_name          = string
    model_name          = optional(string)
  }))
  description = "List of subscription configurations. Each subscription will create a separate Pub/Sub subscription to the same Cloud Run service."
}

variable "max_delivery_attempts" {
  type        = number
  description = "The maximum number of delivery attempts for a message before it is moved to the dead letter topic."
  default     = 5
}

variable "dead_letter_ack_deadline_seconds" {
  type        = number
  description = "The maximum number of seconds that a subscriber has to acknowledge each message pulled from the dead letter subscription."
  default     = 10
}

variable "dead_letter_push_endpoint_path" {
  type        = string
  description = "The path on the Cloud Run service to which messages that fail to be delivered are sent as a POST request."
  default     = "/deadletter"
}

# cloud run configuration
variable "service_name" {
  type        = string
  description = "Name of the service the listener belongs to."
}

variable "listener_name" {
  type        = string
  description = "Name of the listener, not including the name of the event."
}

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
}

variable "vpc_subnetwork" {
  type        = string
  description = "The ID of the VPC subnet to deploy the service to."
}

# scheduler
variable "health_check_interval_minutes" {
  type        = number
  description = "Interval between health checks, in minutes."
  default     = 15
}
