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

variable "domain_name" {
  type        = string
  description = "The domain name of the entire project."
}

variable "mcp_subdomain" {
  type        = string
  description = "The subdomain at which the MCP server is served."
}

variable "api_subdomain" {
  type        = string
  description = "The subdomain at which the API is served. One Front Door endpoint fronts every service there, so the MCP server reaches a service at /rest/<service>/."
}
