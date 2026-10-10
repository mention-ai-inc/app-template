resource "google_storage_bucket" "static-assets" {
  project                     = var.operations_project_id
  name                        = "${var.operations_project_id}--static-assets"
  location                    = "US"
  force_destroy               = true
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
}
