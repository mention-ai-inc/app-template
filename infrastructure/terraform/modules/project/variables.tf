# Constants
variable "project_name" {
  description = "Display name of the GCP project. This is the name that will be displayed in the GCP console."
  type        = string
}

variable "project_id_base" {
  description = "ID of the GCP project, not including the randomly generated suffix."
  type        = string
}

variable "random_project_id" {
  description = "If 'true', a random 4-character alphanmueric suffix will be appended to the project ID."
  type        = string
  default     = "false"
}

variable "organization_id" {
  description = "ID for the GCP organization under which the projects will be managed."
  type        = string
  default     = null
}

variable "folder_id" {
  description = "Folder ID of the project parent."
  type        = string
  default     = null
}

variable "billing_account_id" {
  description = "Billing account ID to be associated with the project."
  type        = string
}

variable "gcp_services" {
  description = "List of GCP services to be enabled for the project."
  type        = list(string)
}

variable "firebase" {
  description = "If true, firebase will be enabled for the project."
  type        = bool
}
