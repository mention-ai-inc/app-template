variable "resource_group_name" {
  type        = string
  description = "Name of the resource group that holds the Cosmos DB account."
}

variable "cosmos_account_name" {
  type        = string
  description = "Name of the Cosmos DB account that holds the watched container."
}

variable "cosmos_database_name" {
  type        = string
  description = "Name of the Cosmos DB SQL database that holds the watched container."
}

variable "watched_container_name" {
  type        = string
  description = "Name of the container whose change feed the trigger reads."
}

variable "service_name" {
  type        = string
  description = "Name of the service that owns the trigger."
}

variable "trigger_name" {
  type        = string
  description = "Name of the trigger, which names its lease container and selects its handler within the trigger pool."
}

variable "document_type" {
  type        = string
  description = "The value of the documentType field the trigger acts on. It replaces the Firestore collection name, because every document type of a service shares one Cosmos container."
}

variable "max_throughput" {
  type        = number
  description = "Autoscale ceiling for the lease container, in request units per second. Ignored on serverless accounts."
  default     = 1000
}

variable "provisioned_throughput" {
  type        = bool
  description = "Whether the account provisions throughput. Serverless accounts reject throughput settings, so feature environments leave this false."
  default     = false
}
