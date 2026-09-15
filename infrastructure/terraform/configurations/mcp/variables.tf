variable "preferred_region" {
  type        = string
  description = "The preferred region for the project. This should be the same for all configurations."
}

variable "github_repo" {
  type        = string
  description = "The name of the GitHub repository, in `owner/repo` form."
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
  description = "The subdomain at which the API the MCP server calls is served."
}

variable "log_retention_days" {
  type        = number
  description = "Days container logs are kept in CloudWatch."
  default     = 30
}
