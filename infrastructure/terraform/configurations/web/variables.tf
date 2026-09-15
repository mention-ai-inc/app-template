variable "preferred_region" {
  type        = string
  description = "The region the AWS provider reads secrets and DNS records in."
}

variable "github_repo" {
  type        = string
  description = "The name of the GitHub repository, in `owner/repo` form."
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
