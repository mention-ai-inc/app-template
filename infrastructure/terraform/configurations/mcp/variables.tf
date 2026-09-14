variable "operations_project_id" {
  type        = string
  description = "The ID of the project where project operations resources are held."
}

variable "preferred_region" {
  type        = string
  description = "The preferred region for the Project. This should be the same for all projects."
}

variable "domain_name" {
  type        = string
  description = "The domain name of the entire project."
}

variable "mcp_subdomain" {
  type        = string
  description = "The subdomain at which the MCP server is served."
}

variable "dns_managed_zone" {
  type        = string
  description = "The name of the DNS managed zone."
}
