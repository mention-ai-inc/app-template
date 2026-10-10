resource "google_pubsub_topic" "dead-letter-topic" {
  project = var.project_id
  name    = join("", [var.feature_environment, var.service_name, "-", var.listener_name, "-dl"])
}
