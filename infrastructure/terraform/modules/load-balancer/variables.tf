variable "project_id" {
  type        = string
  description = "ID of the GCP project the service belongs to."
}

variable "region" {
  type        = string
  description = "The region to deploy to."
}

variable "feature_environment" {
  type        = string
  description = "The environment-specific prefix to use when naming resources. Supplied in order to inject it into the environment for Cloud Run services, so that resources can be correctly accessed in application code."
}

variable "service_name" {
  type        = string
  description = "The name of the service. Not a display name; it is used in resource names."
}

variable "domain_name" {
  type        = string
  description = "Domain name that the API will be deployed to."
}

variable "default_service_account_email" {
  type        = string
  description = "The email address of the IAM service account associated with the default service."
}

variable "default_service_vpc_network" {
  type        = string
  description = "The VPC network to deploy the default service to."
}

variable "default_service_vpc_subnetwork" {
  type        = string
  description = "The subnetwork to deploy the default service to."
}

variable "rest_service_links" {
  type        = map(string)
  description = "A map of service names to the corresponding URLs of their REST services."
}

variable "forwarding_rule_load_balancing_scheme" {
  type        = string
  description = "The load balancing scheme to use for the forwarding rule."
  default     = "EXTERNAL_MANAGED"
}

variable "forwarding_rule_port_range" {
  type        = string
  description = "The range of ports that the forwarding rule will send to the service."
  default     = "443-443"
}

variable "global_address_type" {
  type        = string
  description = "The type of address to reserve, either INTERNAL or EXTERNAL."
  default     = "EXTERNAL"
}

variable "global_address_ip_version" {
  type        = string
  description = "The IP version that will be used by this address."
  default     = "IPV4"
}

variable "dns_managed_zone" {
  type        = string
  description = "The name of the managed zone to create the DNS record in."
}
