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

variable "vercel_team_id" {
  type        = string
  description = "The ID of the Vercel team."
}

variable "app_domain" {
  type        = string
  description = "The domain name of the frontend application."
}

variable "function_default_timeout" {
  type        = number
  description = "The default timeout for functions in seconds."
}

variable "frontend_framework" {
  type        = string
  description = "The frontend framework to be supplied to Vercel."
  default     = "vite"
}
