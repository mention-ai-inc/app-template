variable "name" {
  type        = string
  description = "Name of the cache, including the feature environment prefix."
}

variable "resource_group_name" {
  type        = string
  description = "Name of the resource group the cache belongs to."
}

variable "location" {
  type        = string
  description = "Region the cache is created in."
}

variable "sku_name" {
  type        = string
  description = "Service tier of the cache."
  default     = "Basic"
}

variable "family" {
  type        = string
  description = "Size family of the cache. C for Basic and Standard, P for Premium."
  default     = "C"
}

variable "capacity" {
  type        = number
  description = "Size within the family, which determines the memory available to the cache."
  default     = 1
}

variable "max_memory_policy" {
  type        = string
  description = "Eviction policy applied when the cache is full."
  default     = "allkeys-lru"
}

variable "firewall_rules" {
  type = list(object({
    name     = string
    start_ip = string
    end_ip   = string
  }))
  description = "Address ranges permitted to reach the cache. An empty list leaves the cache reachable by any caller holding the access key over TLS."
  default     = []
}

variable "tags" {
  type        = map(string)
  description = "Tags applied to the cache."
  default     = {}
}
