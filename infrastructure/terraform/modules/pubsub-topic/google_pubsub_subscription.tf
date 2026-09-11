resource "google_pubsub_subscription" "storage-subscription" {
  count = var.storage_subscriber ? 1 : 0

  project = var.project_id
  name    = "${var.feature_environment}${var.topic_name}-storage"
  topic   = google_pubsub_topic.topic.id

  cloud_storage_config {
    bucket = var.storage_bucket
    avro_config {
      write_metadata = true
    }
  }
}

resource "google_pubsub_subscription" "bigquery-subscription" {
  count = var.bigquery_subscriber ? 1 : 0

  project = var.project_id
  name    = "${var.feature_environment}${var.topic_name}-bigquery"
  topic   = google_pubsub_topic.topic.id

  bigquery_config {
    table          = "${var.project_id}.${var.bigquery_dataset_id}.${google_bigquery_table.pubsub_export[0].table_id}"
    write_metadata = true
  }

  depends_on = [google_bigquery_table.pubsub_export]
}
