variable "repository_name" {
  type        = string
  description = "Name of the repository, carrying the feature environment prefix."
}

variable "untagged_image_retention_days" {
  type        = number
  description = "Number of days an untagged image is kept before the lifecycle policy expires it."
  default     = 14
}

variable "tagged_image_retention_count" {
  type        = number
  description = "Number of tagged images kept before the lifecycle policy expires the oldest."
  default     = 50
}

variable "readers" {
  type        = list(string)
  description = "IAM role ARNs granted pull access through the repository policy."
  default     = []
}

variable "writers" {
  type        = list(string)
  description = "IAM role ARNs granted push access through the repository policy."
  default     = []
}
