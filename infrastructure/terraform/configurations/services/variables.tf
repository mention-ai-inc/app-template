variable "preferred_region" {
  type        = string
  description = "The preferred region for the project. This should be the same for all configurations."
}

variable "github_repo" {
  type        = string
  description = "The name of the GitHub repository, in `owner/repo` form."
}

variable "redis_node_type" {
  type        = string
  description = "Instance class of the production cache nodes."
}

variable "feature_redis_node_type" {
  type        = string
  description = "Instance class of feature-environment cache nodes. Kept separate from the production class so capacity shortages can be avoided without changing production."
}

variable "redis_engine_version" {
  type        = string
  description = "Redis engine version the cache runs."
  default     = "7.1"
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
  description = "The domain name of the frontend application. Object stores accept browser uploads from it."
}

variable "services" {
  type        = any
  description = "A map of service names to the infrastructure settings for their components."
}

variable "topics" {
  type        = map(map(string))
  description = "The event topics to be created. Each entry names the topic and says whether its messages are archived and made queryable."
}

variable "audit_retention_days" {
  type        = number
  description = "Retention window for audit-log records, applied as an S3 lifecycle rule and, in production only, an object lock so feature environments stay destroyable."
  default     = 2555
}

variable "log_retention_days" {
  type        = number
  description = "Days container logs are kept in CloudWatch."
  default     = 30
}

variable "python_warnings" {
  type        = string
  description = "The Python warnings to be ignored."
}

variable "alert_email" {
  type        = string
  description = "Address the alarm topic delivers to."
}
