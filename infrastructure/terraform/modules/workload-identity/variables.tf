variable "project_id" {
  type        = string
  description = "The ID of the GCP project in which the Workload Identity Pool resides."
}

variable "id" {
  type        = string
  description = "The ID of the Workload Identity Pool."
}

variable "display_name" {
  type        = string
  description = "The display name of the Workload Identity Pool."
}

variable "pool_description" {
  type        = string
  description = "The human-friendly description of the Workload Identity Pool."
}

variable "issuer_uri" {
  type        = string
  description = "The OIDC issuer URI that represents the pool."
}

variable "service_account_uris" {
  type        = list(string)
  description = "The URIs of the IAM service accounts associated with the pool."
}

variable "attribute_mapping" {
  type        = map(string)
  description = "Attributes mapping to be used for the pool."
}

variable "attribute_condition" {
  type        = string
  description = "The condition that the attribute must satisfy to be used for the pool."
}

variable "member_attribute_name" {
  type        = string
  description = "Name of the attribute to be appended to the member of the service account IAM binding."
}

variable "member_attribute_value" {
  type        = string
  description = "Value of the attribute to be appended to the member of the service account IAM binding."
}
