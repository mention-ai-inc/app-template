resource "google_pubsub_subscription_iam_member" "subscribe-deadletter-topic" {
  for_each = { for idx, sub in var.subscriptions : idx => sub }

  subscription = google_pubsub_subscription.listener-subscription[each.key].id
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:service-${var.project_number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}
