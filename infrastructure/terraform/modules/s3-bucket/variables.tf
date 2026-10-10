variable "name_prefix" {
  description = "Prefix every bucket name starts with. Bucket names are globally unique across all of AWS, so this carries the project's own identity."
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

variable "reader_writer_role_arns" {
  description = "The IAM roles that are granted read and write access to the bucket's objects."
  type        = list(string)
  default     = []
}

variable "force_destroy" {
  description = "Whether the bucket may be destroyed while it still holds objects."
  type        = bool
  default     = true
}
