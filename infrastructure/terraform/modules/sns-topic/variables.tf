variable "feature_environment" {
  type        = string
  description = "The environment-specific prefix to use when naming resources."
}

variable "topic_name" {
  type        = string
  description = "Name of the topic, and the base of the name of every resource derived from it."
}

variable "archive_subscriber" {
  type        = bool
  description = "Whether to deliver every message to S3 through a Kinesis Data Firehose delivery stream."
  default     = false
}

variable "archive_bucket_arn" {
  type        = string
  description = "ARN of the bucket messages are archived to. Required when archive_subscriber is true."
  default     = ""
}

variable "analytics_subscriber" {
  type        = bool
  description = "Whether to register the archived messages as a Glue catalog table so that Athena can query them. Requires archive_subscriber."
  default     = false
}

variable "glue_database_name" {
  type        = string
  description = "Glue database the catalog table is created in. Required when analytics_subscriber is true."
  default     = ""
}

variable "buffering_interval_seconds" {
  type        = number
  description = "Seconds Firehose buffers messages before writing an object."
  default     = 300
}

variable "buffering_size_mb" {
  type        = number
  description = "Megabytes Firehose buffers before writing an object."
  default     = 5
}

variable "publisher_role_arns" {
  type        = list(string)
  description = "IAM roles allowed to publish to the topic."
  default     = []
}
