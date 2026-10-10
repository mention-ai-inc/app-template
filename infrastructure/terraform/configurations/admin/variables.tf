variable "subscription_id" {
  type        = string
  description = "The ID of the Azure subscription every environment is created in."
}

variable "tenant_id" {
  type        = string
  description = "The ID of the Entra ID tenant the subscription belongs to."
}

variable "operations_resource_group_name" {
  type        = string
  description = "The name of the resource group where shared operations resources are held."
}

variable "preferred_region" {
  type        = string
  description = "The preferred region for the estate. This should be the same for all environments."
}

variable "domain_name" {
  type        = string
  description = "The domain name of the entire project."
}

variable "admin_subdomain" {
  type        = string
  description = "The subdomain at which the admin API is served."
}

variable "admin_ip_allowlist" {
  type = list(object({
    name             = string
    ip_address_range = string
  }))
  description = "Address ranges permitted to reach the admin ingress, narrowing who can even attempt a login. The gate that matters is the container app's built-in auth, which terminates Entra sign-in and hands the app an X-MS-CLIENT-PRINCIPAL header; leaving this empty admits every address to the login page and none past it."
  default     = []
}

variable "python_warnings" {
  type        = string
  description = "Value for the PYTHONWARNINGS environment variable."
}
