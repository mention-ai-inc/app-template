module "pubsub-topics" {
  for_each = var.topics
  source   = "../../modules/pubsub-topic"

  project_id                = local.project
  feature_environment       = local.feature_environment
  topic_name                = each.value.name
  storage_subscriber        = lookup(each.value, "storage_subscriber", false)
  storage_bucket            = each.key == "audit_events" ? google_storage_bucket.audit-archive.name : module.pubsub-bucket.bucket_name
  bigquery_subscriber       = lookup(each.value, "bigquery_subscriber", false)
  bigquery_dataset_id       = each.key == "audit_events" ? google_bigquery_dataset.audit_export.dataset_id : google_bigquery_dataset.pubsub_export.dataset_id
  partition_expiration_days = lookup(each.value, "partition_expiration_days", 0)

  depends_on = [
    google_storage_bucket_iam_member.pubsub-storage-create,
    google_storage_bucket_iam_member.pubsub-storage-reader,
    google_bigquery_dataset_iam_member.pubsub-bigquery-writer,
    google_storage_bucket_iam_member.audit-storage-create,
    google_storage_bucket_iam_member.audit-storage-reader,
    google_bigquery_dataset_iam_member.audit-bigquery-writer,
  ]
}
