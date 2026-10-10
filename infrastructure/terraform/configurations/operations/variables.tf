variable "subscription_id" {
  type        = string
  description = "The ID of the Azure subscription every environment is created in. Feature environments are name-prefixed resources inside this one subscription, not subscriptions of their own."
}

variable "tenant_id" {
  type        = string
  description = "The ID of the Entra ID tenant the subscription belongs to."
}

variable "operations_resource_group_name" {
  type        = string
  description = "The name of the resource group holding shared operations resources. It is created by hand before the first apply, because it holds the Terraform state account."
}

variable "production_resource_group_name" {
  type        = string
  description = "The name of the resource group holding production."
}

variable "feature_resource_group_name" {
  type        = string
  description = "The name of the resource group holding every feature environment."
}

variable "preferred_region" {
  type        = string
  description = "Region in which to deploy resources. This should be the same for all environments."
}

variable "github_repo" {
  type        = string
  description = "The name of the GitHub repository to federate against. Provided in the form `owner/repo`."
}

variable "domain_name" {
  type        = string
  description = "The domain name of the entire project."
}

variable "container_registry_name" {
  type        = string
  description = "Globally unique name of the container registry that holds every component's images."
}

variable "operations_key_vault_name" {
  type        = string
  description = "Globally unique name of the key vault holding secrets shared by every environment."
}

variable "production_key_vault_name" {
  type        = string
  description = "Globally unique name of the key vault holding production secrets."
}

variable "feature_key_vault_name" {
  type        = string
  description = "Globally unique name of the key vault holding feature-environment secrets."
}

variable "operations_storage_account_name" {
  type        = string
  description = "Globally unique name of the operations storage account. Blob containers live inside a storage account, so there is one account per environment rather than one bucket per purpose."
}

variable "production_storage_account_name" {
  type        = string
  description = "Globally unique name of the production storage account."
}

variable "feature_storage_account_name" {
  type        = string
  description = "Globally unique name of the feature-environment storage account."
}

variable "blob_cors_origins" {
  type        = list(string)
  description = "Origins permitted to read and write blobs directly. Azure applies CORS to the whole storage account rather than to an individual container."
  default     = []
}

variable "production_servicebus_namespace_name" {
  type        = string
  description = "Globally unique name of the production Service Bus namespace."
}

variable "feature_servicebus_namespace_name" {
  type        = string
  description = "Globally unique name of the feature-environment Service Bus namespace."
}

variable "production_cosmos_account_name" {
  type        = string
  description = "Globally unique name of the production Cosmos DB account."
}

variable "feature_cosmos_account_name" {
  type        = string
  description = "Globally unique name of the feature-environment Cosmos DB account, shared by every feature environment and partitioned by database name."
}

variable "production_cosmos_backup_retention_hours" {
  type        = number
  description = "Retention window for production Cosmos DB periodic backups. Cosmos DB caps this at 720 hours."
  default     = 720
}

variable "production_container_app_environment_name" {
  type        = string
  description = "Name of the production Container App Environment."
}

variable "feature_container_app_environment_name" {
  type        = string
  description = "Name of the Container App Environment shared by every feature environment."
}

variable "production_log_retention_days" {
  type        = number
  description = "Retention window for production logs, in days."
  default     = 90
}

variable "feature_log_retention_days" {
  type        = number
  description = "Retention window for feature-environment logs, in days."
  default     = 30
}

variable "production_front_door_profile_name" {
  type        = string
  description = "Name of the production Front Door profile. One profile serves every production endpoint, because the base charge is levied per profile."
}

variable "feature_front_door_profile_name" {
  type        = string
  description = "Name of the Front Door profile shared by every feature environment. Each feature environment adds its own endpoint, origins, and routes to it, so the base charge is paid once rather than per environment."
}

variable "front_door_sku_name" {
  type        = string
  description = "Service tier of the Front Door profiles. Standard_AzureFrontDoor carries path-based routing and managed certificates; Premium_AzureFrontDoor adds private link origins and managed WAF rules."
  default     = "Standard_AzureFrontDoor"
}

variable "front_door_response_timeout_seconds" {
  type        = number
  description = "How long Front Door waits for the first byte from an origin before it gives up."
  default     = 120
}
