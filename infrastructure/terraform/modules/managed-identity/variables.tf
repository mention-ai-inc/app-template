variable "name" {
  type        = string
  description = "Name of the user-assigned managed identity, including the feature environment prefix."
}

variable "resource_group_name" {
  type        = string
  description = "Name of the resource group the identity belongs to."
}

variable "location" {
  type        = string
  description = "Region in which the identity is created."
}

variable "role_assignments" {
  type = list(object({
    role  = string
    scope = string
  }))
  description = "Built-in role definitions to grant to the identity, each at the scope it applies to."
  default     = []
}

variable "tags" {
  type        = map(string)
  description = "Tags applied to the identity."
  default     = {}
}
