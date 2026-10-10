variable "project_id" {
  type        = string
  description = "ID of the GCP project the topic belongs to."
}

variable "feature_environment" {
  type        = string
  description = "The environment-specific prefix to use when naming resources. Supplied in order to inject it into the environment for Cloud Run services, so that resources can be correctly accessed in application code."
}

variable "topic_name" {
  type        = string
  description = "Name of the PubSub topic, and the base of the name of the schema."
}

variable "storage_subscriber" {
  type        = bool
  description = "Whether to create a subscriber to the topic that writes all messages to a GCS bucket."
}

variable "storage_bucket" {
  type        = string
  description = "Name of the GCS bucket to write messages to, if enabled."
  default     = ""
}

variable "bigquery_subscriber" {
  type        = bool
  description = "Whether to create a subscriber to the topic that writes all messages to a BigQuery table."
  default     = false
}

variable "bigquery_dataset_id" {
  type        = string
  description = "BigQuery dataset ID to create the topic's export table in. Required if bigquery_subscriber is true."
  default     = ""
}

variable "partition_expiration_days" {
  type        = number
  description = "If > 0, day-partition the BigQuery export table on publish_time and expire partitions after this many days. Used to enforce audit-log retention."
  default     = 0
}
