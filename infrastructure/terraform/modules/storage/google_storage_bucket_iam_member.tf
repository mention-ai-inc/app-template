resource "google_storage_bucket_iam_member" "service-artifacts-admin" {
  for_each = toset(var.service_accounts)

  bucket = google_storage_bucket.bucket.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${each.value}"
}
