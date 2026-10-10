variable "table_name" {
  type        = string
  description = "Name of the table, carrying the feature environment prefix. Every service shares one table and namespaces its partition keys."
}

variable "is_production" {
  type        = bool
  description = "Whether the table belongs to production, which turns on deletion protection and point-in-time recovery."
}
