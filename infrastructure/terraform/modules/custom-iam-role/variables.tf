variable "project_id" {
  description = "ID of the GCP project the service account belongs to."
  type        = string
}

variable "role_id" {
  description = "ID for the custom role. This is the role name used in IAM policy bindings."
  type        = string
}

variable "title" {
  description = "Human-friendly display name for the custom role."
  type        = string
}

variable "description" {
  description = "Human-friendly description for the custom role."
  type        = string
}

variable "permissions" {
  description = "List of permissions to grant to the custom role."
  type        = list(string)
}

variable "user_members" {
  description = "List of emails for user accounts that are granted the role."
  type        = list(string)
  default     = []
}

variable "service_account_members" {
  description = "List of emails for service accounts that are granted the role."
  type        = list(string)
  default     = []
}
