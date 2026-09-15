variable "role_name" {
  type        = string
  description = "Name of the role GitHub Actions assumes."
}

variable "oidc_provider_arn" {
  type        = string
  description = "ARN of the account's GitHub OIDC provider."
}

variable "oidc_provider_host" {
  type        = string
  description = "Host of the OIDC issuer, which prefixes the subject and audience claims in the trust policy."
  default     = "token.actions.githubusercontent.com"
}

variable "github_repo" {
  type        = string
  description = "The repository allowed to assume the role, in owner/repo form."
}

variable "subject_patterns" {
  type        = list(string)
  description = "Subject claims allowed to assume the role, relative to the repository."
  default     = ["*"]
}

variable "actions" {
  type        = list(string)
  description = "Actions granted to the role by its inline policy."
  default     = []
}

variable "resources" {
  type        = list(string)
  description = "Resources the inline policy's actions apply to."
  default     = ["*"]
}

variable "policy_arns" {
  type        = list(string)
  description = "Managed policies attached to the role."
  default     = []
}

variable "maximum_session_duration_seconds" {
  type        = number
  description = "Longest a set of credentials issued for this role stays valid."
  default     = 3600
}
