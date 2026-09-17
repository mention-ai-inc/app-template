variable "project_id" {
  type        = string
  description = "The Google Cloud project ID"
}

variable "zone" {
  type        = string
  description = "The zone where the Redis instance will be deployed"
}

variable "subnetwork" {
  type        = string
  description = "The subnetwork for the Redis instance"
}

variable "environment_prefix" {
  type        = string
  description = "Prefix for resource naming (e.g., feature environment)"
  default     = ""
}

variable "disk_size_gb" {
  type        = number
  description = "The size of the disk for the Redis instance"
  default     = 10
}

variable "machine_type" {
  type        = string
  description = "The machine type of the Redis instance"
  default     = "e2-micro"
}

variable "disk_image" {
  type        = string
  description = "The disk image of the Redis instance"
  default     = "debian-cloud/debian-12"
}

variable "is_production" {
  type        = bool
  description = "Whether this is a production environment (affects external IP and tags)"
  default     = false
}

variable "operations_project_id" {
  type        = string
  description = "The operations project ID where the public-images artifact registry lives"
}

variable "service_account_email" {
  type        = string
  description = "Email of the service account to attach to the instance"
}

variable "max_memory" {
  type        = string
  description = "The maximum memory for Redis (e.g., '900mb', '2gb')"
}

variable "redis_version" {
  type        = string
  description = "redis/redis-stack-server Docker image version tag (Redis Stack bundles RedisBloom, used by the glossary write-in counter)"
  default     = null
}

variable "redis_exporter_version" {
  type        = string
  description = "Redis Exporter Docker image version tag"
  default     = null
}

variable "redis_password" {
  type        = string
  description = "Redis password (must be provided by caller)"
  sensitive   = true
}
