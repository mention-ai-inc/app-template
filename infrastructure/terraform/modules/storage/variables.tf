variable "project_id" {
  description = "ID of the GCP project the bucket belongs to."
  type        = string
}

variable "feature_environment" {
  description = "The environment-specific prefix to use when naming resources."
  type        = string
}

variable "service" {
  description = "The name of the service that the bucket belongs to."
  type        = string
  default     = ""
}

variable "bucket_name" {
  description = "The name of the bucket."
  type        = string
}

variable "cors_origins" {
  description = "The origins that are allowed to access the bucket."
  type        = list(string)
  default     = []
}

variable "service_accounts" {
  description = "The service accounts that are granted access to the bucket."
  type        = list(string)
  default     = []
}
