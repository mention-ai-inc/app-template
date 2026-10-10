resource "google_pubsub_topic" "topic" {
  project = var.project_id
  name    = join("", [var.feature_environment, var.topic_name])
}
