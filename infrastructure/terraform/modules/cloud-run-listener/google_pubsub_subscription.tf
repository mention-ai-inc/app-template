resource "google_pubsub_subscription" "listener-subscription" {
  for_each = { for idx, sub in var.subscriptions : idx => sub }

  project              = var.project_id
  name                 = join("", [var.feature_environment, var.service_name, "-", var.listener_name, "-", each.key])
  topic                = "projects/${var.project_id}/topics/${var.feature_environment}${each.value.topic_name}"
  filter               = "(${join(" OR ", [for service_name in split("|", each.value.source_service_name) : "attributes.service = \"${service_name}\""])}) AND (${join(" OR ", [for event_name in split("|", each.value.event_name) : "attributes.event = \"${event_name}\""])})${each.value.model_name != null && each.value.model_name != "" ? " AND (${join(" OR ", [for model_name in split("|", each.value.model_name) : "attributes.model_name = \"${model_name}\""])})" : ""}"
  ack_deadline_seconds = var.timeout_seconds

  push_config {
    push_endpoint = google_cloud_run_v2_service.listener.uri
    oidc_token {
      service_account_email = var.service_account_email
    }
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dead-letter-topic.id
    max_delivery_attempts = var.max_delivery_attempts
  }
}

resource "google_pubsub_subscription" "dead-letter-topic-default-subscription" {
  project              = var.project_id
  name                 = join("", [var.feature_environment, var.service_name, "-", var.listener_name, "-dl-sub"])
  topic                = google_pubsub_topic.dead-letter-topic.name
  ack_deadline_seconds = var.dead_letter_ack_deadline_seconds

  push_config {
    push_endpoint = join("", [google_cloud_run_v2_service.listener.uri, var.dead_letter_push_endpoint_path])
    oidc_token {
      service_account_email = var.service_account_email
    }
  }
}
