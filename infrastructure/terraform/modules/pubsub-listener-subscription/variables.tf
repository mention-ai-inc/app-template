# admin
variable "project_id" {
  type        = string
  description = "ID of the GCP project the subscriptions belong to."
}

variable "project_number" {
  type        = string
  description = "Number of the GCP project, used to name the Pub/Sub service agent."
}

variable "feature_environment" {
  type        = string
  description = "The environment-specific prefix to use when naming resources."
}

variable "service_name" {
  type        = string
  description = "Name of the service that owns the listener."
}

variable "listener_name" {
  type        = string
  description = "Name of the listener, which names the subscriptions and selects its route within the listener pool."
}

variable "subscriptions" {
  type = list(object({
    event_name          = string
    source_service_name = string
    topic_name          = string
    model_name          = optional(string)
  }))
  description = "List of subscription configurations. Each subscription will create a separate Pub/Sub subscription pushing to the same listener route."
}

# routing
variable "push_base_uri" {
  type        = string
  description = "Base URL of the listener pool hosting this listener. The listener's route is appended to it."
}

variable "service_account_email" {
  type        = string
  description = "Email address of the service account Pub/Sub mints its OIDC token as when pushing."
}

variable "dead_letter_push_endpoint_path" {
  type        = string
  description = "Path appended to the listener's route to acknowledge and drain dead-lettered messages."
  default     = "/deadletter"
}

# delivery
variable "timeout_seconds" {
  type        = number
  description = "Acknowledgement deadline for the subscription, in seconds."
  default     = 60
}

variable "max_delivery_attempts" {
  type        = number
  description = "Number of delivery attempts before a message is forwarded to the dead-letter topic."
  default     = 5
}

variable "dead_letter_ack_deadline_seconds" {
  type        = number
  description = "Acknowledgement deadline for the dead-letter subscription, in seconds."
  default     = 10
}
