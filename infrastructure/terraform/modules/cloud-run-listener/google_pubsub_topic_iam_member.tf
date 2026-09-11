resource "google_pubsub_topic_iam_member" "publish-deadletter-topic" {
  topic  = google_pubsub_topic.dead-letter-topic.id
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:service-${var.project_number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}
