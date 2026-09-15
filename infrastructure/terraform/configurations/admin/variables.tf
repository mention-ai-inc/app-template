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

variable "admin_subdomain" {
  type        = string
  description = "The subdomain at which the admin API is served."
}

variable "python_warnings" {
  type        = string
  description = "Value for the PYTHONWARNINGS environment variable."
}

variable "oidc_issuer" {
  type        = string
  description = "Issuer of the OIDC provider the load balancer authenticates staff against before any request reaches the admin API."
}

variable "oidc_authorization_endpoint" {
  type        = string
  description = "Authorization endpoint of the OIDC provider."
}

variable "oidc_token_endpoint" {
  type        = string
  description = "Token endpoint of the OIDC provider."
}

variable "oidc_user_info_endpoint" {
  type        = string
  description = "User info endpoint of the OIDC provider."
}

variable "oidc_scope" {
  type        = string
  description = "Scopes requested of the OIDC provider."
  default     = "openid email profile"
}

variable "oidc_session_timeout_seconds" {
  type        = number
  description = "Seconds an authenticated session at the load balancer stays valid."
  default     = 43200
}

variable "rate_limit_per_five_minutes" {
  type        = number
  description = "Requests a single address may make in five minutes before the web ACL blocks it."
  default     = 600
}

variable "log_retention_days" {
  type        = number
  description = "Days container logs are kept in CloudWatch."
  default     = 30
}
