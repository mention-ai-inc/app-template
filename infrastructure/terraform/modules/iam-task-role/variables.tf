variable "role_name" {
  description = "Name of the IAM role. Carries the feature environment prefix so that every environment has its own role."
  type        = string
}

variable "trusted_services" {
  description = "AWS service principals allowed to assume the role."
  type        = list(string)
  default     = ["ecs-tasks.amazonaws.com"]
}

variable "actions" {
  description = "Actions granted to the role by its inline policy."
  type        = list(string)
  default     = []
}

variable "resources" {
  description = "Resources the inline policy's actions apply to."
  type        = list(string)
  default     = ["*"]
}

variable "policy_arns" {
  description = "Managed policies attached to the role."
  type        = list(string)
  default     = []
}

variable "assumable_by_role_arns" {
  description = "IAM role ARNs allowed to assume this role. The AWS counterpart of service-account impersonation."
  type        = list(string)
  default     = []
}

variable "assumable_by_user_arns" {
  description = "IAM user or principal ARNs allowed to assume this role."
  type        = list(string)
  default     = []
}

variable "permissions_boundary" {
  description = "ARN of a permissions boundary to attach to the role."
  type        = string
  default     = null
}
