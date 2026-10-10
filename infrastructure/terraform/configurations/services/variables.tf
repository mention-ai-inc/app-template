variable "subscription_id" {
  type        = string
  description = "The ID of the Azure subscription every environment is created in."
}

variable "tenant_id" {
  type        = string
  description = "The ID of the Entra ID tenant the subscription belongs to."
}

variable "operations_resource_group_name" {
  type        = string
  description = "The name of the resource group where shared operations resources are held."
}

variable "preferred_region" {
  type        = string
  description = "The preferred region for the estate. This should be the same for all environments."
}

variable "github_repo" {
  type        = string
  description = "The name of the GitHub repository, in the form `owner/repo`."
}

variable "cosmos_max_throughput" {
  type        = number
  description = "Autoscale ceiling for the production Cosmos DB database, in request units per second. Feature environments run on a serverless account and ignore this."
  default     = 4000
}

variable "cosmos_lease_max_throughput" {
  type        = number
  description = "Autoscale ceiling for a change feed lease container, in request units per second."
  default     = 1000
}

variable "redis_sku_name" {
  type        = string
  description = "Service tier of the production cache."
  default     = "Standard"
}

variable "redis_family" {
  type        = string
  description = "Size family of the production cache."
  default     = "C"
}

variable "redis_capacity" {
  type        = number
  description = "Size within the family of the production cache."
  default     = 1
}

variable "feature_redis_sku_name" {
  type        = string
  description = "Service tier of feature-environment caches. Kept separate from the production tier so capacity shortages can be avoided without changing production."
  default     = "Basic"
}

variable "feature_redis_family" {
  type        = string
  description = "Size family of feature-environment caches."
  default     = "C"
}

variable "feature_redis_capacity" {
  type        = number
  description = "Size within the family of feature-environment caches."
  default     = 0
}

variable "domain_name" {
  type        = string
  description = "The domain name of the entire project."
}

variable "api_subdomain" {
  type        = string
  description = "The subdomain of the main domain under which the API is served. Container Apps managed ingress binds one hostname per app, so each service is served at <service>.<api_subdomain>.<domain_name>."
}

variable "app_domain" {
  type        = string
  description = "The domain name of the frontend application."
}

variable "services" {
  type        = any
  description = "A map of service names to the infrastructure settings for their components."
}

variable "topics" {
  type        = map(map(string))
  description = "The list of Service Bus topics to be created. The map contains the topic name and whether it is archived."
}

variable "audit_retention_days" {
  type        = number
  description = "Retention window for the audit archive container, applied as a blob immutability policy and locked in production only so feature environments stay destroyable."
  default     = 2555
}

variable "python_warnings" {
  type        = string
  description = "The Python warnings to be ignored."
}
