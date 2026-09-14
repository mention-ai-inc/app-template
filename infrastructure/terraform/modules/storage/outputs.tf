output "bucket_name" {
  description = "The name of the bucket."
  value       = google_storage_bucket.bucket.name
}
