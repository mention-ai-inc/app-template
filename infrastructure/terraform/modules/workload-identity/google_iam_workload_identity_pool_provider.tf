resource "google_iam_workload_identity_pool_provider" "provider" {
  project                            = var.project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.pool.workload_identity_pool_id
  workload_identity_pool_provider_id = var.id
  display_name                       = var.display_name
  attribute_mapping                  = var.attribute_mapping
  attribute_condition                = var.attribute_condition
  oidc {
    issuer_uri = var.issuer_uri
  }
}
