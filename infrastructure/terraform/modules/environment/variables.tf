variable "feature_resource_group_name" {
  type        = string
  description = "Name of the resource group that holds every feature environment. This is provided as a variable so that it can be pulled from the operations configuration."
}

variable "production_resource_group_name" {
  type        = string
  description = "Name of the resource group that holds production. This is provided as a variable so that it can be pulled from the operations configuration."
}
