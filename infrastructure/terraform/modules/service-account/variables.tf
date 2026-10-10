variable "project_id" {
  description = "ID of the GCP project the service account belongs to."
  type        = string
}

variable "account_id" {
  description = "ID for the service account. This is the username portion of the email associated with the service account."
  type        = string
}

variable "roles" {
  description = "List of roles to grant to the service account."
  type        = list(string)
}

variable "user_impersonaters" {
  description = "List of emails for user accounts that are granted access to impersonate the service account."
  type        = list(string)
  default     = []
}

variable "service_account_impersonaters" {
  description = "List of emails for service accounts that are granted access to impersonate the service account."
  type        = list(string)
  default     = []
}
