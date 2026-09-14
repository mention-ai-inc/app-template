variable "project_id" {
  type        = string
  description = "The ID of the GCP project in which the worker is deployed."
}

variable "region" {
  type        = string
  description = "Region where the instances will be deployed."
}

variable "zone" {
  type        = string
  description = "Zone where the instances will be deployed."
}

variable "feature_environment" {
  type        = string
  description = "The environment-specific prefix to use when naming resources."
}

variable "service_name" {
  type        = string
  description = "Name of the service the worker belongs to."
  default     = null
}

variable "worker_name" {
  type        = string
  description = "Name of the worker."
}

variable "machine_type" {
  type        = string
  description = "Machine type for all instances in the group."
  default     = "e2-medium"
}

variable "image_uri" {
  type        = string
  description = "Docker image to run on the instances. Because this is managed outside of Terraform, this is essentially the startup container only. Note that providing the container intended to be used from the start does not work because Docker breaks when the instance is created with a non-existent image and then reset after the image begins existing (root cause unknown)."
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "command" {
  type        = list(string)
  description = "The command to pass to the container."
  default     = null
}

variable "service_account_email" {
  type        = string
  description = "Email of the service account to use for the instances."
}

variable "env" {
  type        = map(string)
  description = "Environment variables to set in the container."
  default     = {}
}

variable "subnetwork" {
  type        = string
  description = "Subnetwork to deploy the instances in."
}

variable "disk_image" {
  type        = string
  description = "Disk image to use for the instances."
  default     = "projects/cos-cloud/global/images/cos-105-17412-156-59"
}

variable "spot_instance" {
  type        = bool
  description = "Whether to use spot instances for the instances."
  default     = false
}

variable "minimum_instances" {
  type        = number
  description = "Minimum number of instances in the group."
  default     = 0
}

variable "maximum_instances" {
  type        = number
  description = "Maximum number of instances in the group."
  default     = 1
}

variable "cooldown_period" {
  type        = number
  description = "Cooldown period for the autoscaler."
  default     = 60
}

variable "target_cpu_utilization" {
  type        = number
  description = "Target CPU utilization for the autoscaler."
  default     = 0.6
}

variable "needs_external_ip" {
  type        = bool
  description = "Whether the instances need an external IP. This is required for the instances to be able to communicate with the public internet."
  default     = false
}
