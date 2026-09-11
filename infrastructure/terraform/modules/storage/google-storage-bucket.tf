resource "google_storage_bucket" "bucket" {
  project                     = var.project_id
  name                        = "${var.project_id}--${var.feature_environment}${var.service}-${var.bucket_name}"
  location                    = "US"
  force_destroy               = true
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"

  dynamic "cors" {
    for_each = length(var.cors_origins) > 0 ? [1] : []

    content {
      origin          = var.cors_origins
      method          = ["GET", "PUT"]
      response_header = ["Content-Type"]
      max_age_seconds = 3600
    }
  }
}
