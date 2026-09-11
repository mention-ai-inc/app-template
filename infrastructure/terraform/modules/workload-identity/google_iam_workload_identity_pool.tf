resource "google_iam_workload_identity_pool" "pool" {
  project                   = var.project_id
  workload_identity_pool_id = var.id
  display_name              = var.display_name
  description               = var.pool_description
  disabled                  = false
}
