# base
variable "organization_id" {
  type        = string
  description = "The ID of the GCP organization in which the Project will be created."
}

variable "folder_id" {
  type        = string
  description = "The ID of the GCP folder in which the Project will be created."
}

variable "billing_account_id" {
  type        = string
  description = "The ID of the GCP billing account associated with the Project. This should be the same for all projects."
}

variable "operations_project_id" {
  type        = string
  description = "The ID of the Project in which the project operations resources will be created."
}

variable "operations_project_number" {
  type        = string
  description = "The number of the Project in which the project operations resources will be created."
}

variable "github_repo" {
  type        = string
  description = "The name of the GitHub repository to connect service accounts to. Provided in the form `owner/repo`."
}

variable "gcp_services" {
  type        = list(string)
  description = "The list of GCP services enabled in the Project. This should be the same for all projects."
}

variable "preferred_region" {
  type        = string
  description = "Region in which to deploy resources in the operations project."
}

# networking
variable "compute_instances_ip_cidr_range" {
  type        = string
  description = "The IP CIDR range to use for Compute instances."
}

