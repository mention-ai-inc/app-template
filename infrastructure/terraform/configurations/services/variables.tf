# base
variable "operations_project_id" {
  type        = string
  description = "The ID of the project where project operations resources are held."
}

variable "preferred_region" {
  type        = string
  description = "The preferred region for the Project. This should be the same for all projects."
}

variable "preferred_zone" {
  type        = string
  description = "The preferred zone for production compute instances."
}

variable "feature_preferred_zone" {
  type        = string
  description = "The preferred zone for feature-environment compute instances. Kept separate from preferred_zone so capacity shortages can be avoided without moving production."
}

variable "github_repo" {
  type        = string
  description = "The URL of the GitHub repository."
}

# persistence
variable "feature_persistence_machine_type" {
  type        = string
  description = "Machine type for feature-environment Redis instances. Kept separate from production machine types so capacity shortages can be avoided without changing production."
}

variable "redis_machine_type" {
  type        = string
  description = "The machine type of the Redis instance."
}

variable "redis_disk_image" {
  type        = string
  description = "The disk image of the Redis instance."
  default     = "debian-cloud/debian-12"
}

variable "redis_max_memory" {
  type        = string
  description = "The maximum memory of the Redis instance."
}

variable "redis_disk_size_gb" {
  type        = number
  description = "The size of the persistent disk for Redis data."
  default     = 10
}

# api
variable "dns_managed_zone" {
  type        = string
  description = "The name of the DNS managed zone."
}

variable "domain_name" {
  type        = string
  description = "The domain name of the entire project."
}

variable "api_subdomain" {
  type        = string
  description = "The subdomain of the main domain at which the API is served."
}

variable "app_domain" {
  type        = string
  description = "The domain name of the frontend application."
}

# services
variable "services" {
  type        = any
  description = "A map of service names to the infrastructure settings for their components."
}

# events
variable "topics" {
  type        = map(map(string))
  description = "The list of Pub/Sub topics to be created. The map contains the topic ID and schema."
}

variable "audit_retention_days" {
  type        = number
  description = "Retention window for audit-log records in BigQuery (partition expiration) and the GCS archive (bucket retention, applied and locked in production only so feature environments stay destroyable)."
  default     = 2555
}

# config
variable "python_warnings" {
  type        = string
  description = "The Python warnings to be ignored."
}
