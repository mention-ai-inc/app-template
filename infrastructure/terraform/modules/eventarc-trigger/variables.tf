# admin
variable "project_id" {
  type        = string
  description = "ID of the GCP project the trigger belongs to."
}

variable "region" {
  type        = string
  description = "Region where the trigger will be created. Used when a resource asks for region or location."
}

variable "feature_environment" {
  type        = string
  description = "The environment-specific prefix to use when naming resources."
}

variable "service_name" {
  type        = string
  description = "Name of the service that owns the trigger."
}

variable "trigger_name" {
  type        = string
  description = "Name of the trigger, which names the Eventarc trigger and selects its route within the trigger pool."
}

# firestore
variable "firestore_collection" {
  type        = string
  description = "The service-owned Firestore collection whose documents the trigger matches."
}

variable "firestore_event_type" {
  type        = string
  description = "The Firestore document event the trigger matches, such as written or created."
}

# routing
variable "pool_cloud_run_name" {
  type        = string
  description = "Name of the trigger pool Cloud Run service that hosts this trigger's route."
}

variable "service_account_email" {
  type        = string
  description = "Email address of the service account Eventarc invokes the destination as."
}
