# buckets

module "cache-buckets" {
  for_each = var.services
  source   = "../../modules/storage"

  project_id          = local.project
  feature_environment = local.feature_environment
  service             = each.key
  bucket_name         = "cache"
  service_accounts    = [module.service-service-account[each.key].email]
}

module "pubsub-bucket" {
  source = "../../modules/storage"

  project_id          = local.project
  feature_environment = local.feature_environment
  bucket_name         = "pubsub"
}

resource "google_bigquery_dataset" "pubsub_export" {
  project       = local.project
  dataset_id    = "${local.feature_environment}pubsub_export"
  friendly_name = "Pub/Sub export"
  description   = "Pub/Sub topic messages exported to BigQuery"
  location      = "US"

  delete_contents_on_destroy = true
}

resource "google_bigquery_dataset_iam_member" "pubsub-bigquery-writer" {
  project    = local.project
  dataset_id = google_bigquery_dataset.pubsub_export.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:service-${local.project_number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_bigquery_dataset" "audit_export" {
  project       = local.project
  dataset_id    = "${local.feature_environment}audit_export"
  friendly_name = "Audit log export"
  description   = "Tamper-evident audit events exported to BigQuery, retained per policy."
  location      = "US"

  delete_contents_on_destroy = !local.is_production
}

resource "google_bigquery_dataset_iam_member" "audit-bigquery-writer" {
  project    = local.project
  dataset_id = google_bigquery_dataset.audit_export.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:service-${local.project_number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_storage_bucket" "audit-archive" {
  project                     = local.project
  name                        = "${local.project}--${local.feature_environment}audit-archive"
  location                    = "US"
  force_destroy               = !local.is_production
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  dynamic "retention_policy" {
    for_each = local.is_production ? [true] : []
    content {
      retention_period = var.audit_retention_days * 24 * 60 * 60
      is_locked        = true
    }
  }
}

resource "google_storage_bucket_iam_member" "audit-storage-create" {
  bucket = google_storage_bucket.audit-archive.name
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:service-${local.project_number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_storage_bucket_iam_member" "audit-storage-reader" {
  bucket = google_storage_bucket.audit-archive.name
  role   = "roles/storage.legacyBucketReader"
  member = "serviceAccount:service-${local.project_number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

# grant the pubsub service account the ability to publish to the pubsub bucket
resource "google_storage_bucket_iam_member" "pubsub-storage-create" {
  bucket = module.pubsub-bucket.bucket_name
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:service-${local.project_number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

resource "google_storage_bucket_iam_member" "pubsub-storage-reader" {
  bucket = module.pubsub-bucket.bucket_name
  role   = "roles/storage.legacyBucketReader"
  member = "serviceAccount:service-${local.project_number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

# grant each service account the ability to read from the operations project's static assets bucket
resource "google_storage_bucket_iam_member" "service-static-assets-reader" {
  for_each = var.services

  bucket = "${var.operations_project_id}--static-assets"
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${module.service-service-account[each.key].email}"
}
