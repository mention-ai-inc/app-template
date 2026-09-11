resource "google_service_account_iam_member" "service-account" {
  count = length(var.service_account_uris)

  service_account_id = var.service_account_uris[count.index]
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.pool.name}/attribute.${var.member_attribute_name}/${var.member_attribute_value}"
}
