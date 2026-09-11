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

# firestore eventarc
variable "firestore_collection" {
  type        = string
  description = "Name of the Firestore collection to listen to events from."
}

variable "firestore_event_type" {
  type        = string
  description = "Type of Firestore event to listen to (e.g., document_written, document_deleted)."
}

# cloud run configuration
variable "service_name" {
  type        = string
  description = "Name of the service the function belongs to."
}

variable "trigger_name" {
  type        = string
  description = "Name of the trigger."
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