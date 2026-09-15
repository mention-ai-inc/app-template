variable "storage_account_id" {
  type        = string
  description = "Resource ID of the storage account the container is created in. Azure has no top-level bucket, so every container lives inside one account per environment."
}

variable "feature_environment" {
  type        = string
  description = "The environment-specific prefix to use when naming resources."
}

variable "service" {
  type        = string
  description = "The name of the service that the container belongs to."
  default     = ""
}

variable "container_name" {
  type        = string
  description = "The name of the container."
}

variable "principal_ids" {
  type        = map(string)
  description = "Object IDs of the principals granted read and write access to the container's blobs, keyed by a static name. A principal id is not known until the identity it belongs to exists, so it cannot be the key."
  default     = {}
}

variable "reader_principal_ids" {
  type        = map(string)
  description = "Object IDs of the principals granted read-only access to the container's blobs, keyed by a static name."
  default     = {}
}
