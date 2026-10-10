# base
variable "operations_project_id" {
  type        = string
  description = "The ID of the project where project operations resources are held."
}

variable "preferred_region" {
  type        = string
  description = "The preferred region for the Project. This should be the same for all projects."
}

variable "github_repo" {
  type        = string
  description = "The URL of the GitHub repository."
}

variable "vercel_team_id" {
  type        = string
  description = "The ID of the Vercel team."
}

# vercel
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
