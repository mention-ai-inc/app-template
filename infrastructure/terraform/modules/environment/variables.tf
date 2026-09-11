variable "feature_project_id" {
  type        = string
  description = "Project ID for the feature project. This is provided as a variable so that it can be pulled from the operations configuration."
}

variable "production_project_id" {
  type        = string
  description = "Project ID for the production project. This is provided as a variable so that it can be pulled from the operations configuration."
}
