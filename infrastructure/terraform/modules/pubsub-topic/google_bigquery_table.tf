resource "google_bigquery_table" "pubsub_export" {
  count = var.bigquery_subscriber ? 1 : 0

  project    = var.project_id
  dataset_id = var.bigquery_dataset_id
  table_id   = replace(var.topic_name, "-", "_")

  schema = jsonencode([
    { name = "message_id", type = "STRING", mode = "REQUIRED" },
    { name = "publish_time", type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "subscription_name", type = "STRING", mode = "REQUIRED" },
    { name = "attributes", type = "JSON", mode = "REQUIRED" },
    { name = "data", type = "JSON", mode = "REQUIRED" },
  ])

  dynamic "time_partitioning" {
    for_each = var.partition_expiration_days > 0 ? [1] : []
    content {
      type          = "DAY"
      field         = "publish_time"
      expiration_ms = var.partition_expiration_days * 24 * 60 * 60 * 1000
    }
  }

  deletion_protection = var.feature_environment == ""
}
