variable "profile_id" {
  type        = string
  description = "Resource ID of the Front Door profile the endpoint belongs to. The profile is an environment-level resource created once in the operations configuration and shared by every feature environment, because its base charge is per profile."
}

variable "resource_group_name" {
  type        = string
  description = "Name of the resource group the catchall server belongs to."
}

variable "location" {
  type        = string
  description = "Region the catchall server is deployed to."
}

variable "feature_environment" {
  type        = string
  description = "The environment-specific prefix to use when naming resources and when building the API hostname."
}

variable "service_name" {
  type        = string
  description = "The name of the endpoint. Not a display name; it is used in resource names."
}

variable "domain_name" {
  type        = string
  description = "Hostname the API is served at, before the feature environment prefix is applied."
}

variable "dns_zone_name" {
  type        = string
  description = "Name of the Azure DNS zone that holds the API hostname's records."
}

variable "dns_zone_resource_group_name" {
  type        = string
  description = "Name of the resource group that holds the DNS zone."
}

variable "dns_zone_id" {
  type        = string
  description = "Resource ID of the Azure DNS zone, handed to the custom domain so that Front Door can see the validation record it is waiting on."
}

variable "rest_service_origins" {
  type        = map(string)
  description = "A map of service names to the hostname of their REST server's Container App. Each becomes an origin reached at /rest/<service>/*."
}

variable "default_identity_id" {
  type        = string
  description = "Resource ID of the managed identity the catchall server runs as."
}

variable "container_app_environment_id" {
  type        = string
  description = "Resource ID of the Container App Environment that hosts the catchall server."
}

variable "registry_login_server" {
  type        = string
  description = "Login server of the container registry the catchall image is pulled from."
}

variable "health_probe_interval_seconds" {
  type        = number
  description = "Interval between origin health probes, in seconds."
  default     = 60
}

variable "origin_response_timeout_seconds" {
  type        = number
  description = "How long Front Door waits for the first byte from an origin before it gives up."
  default     = 60
}
