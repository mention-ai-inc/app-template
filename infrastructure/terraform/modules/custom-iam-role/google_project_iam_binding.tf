resource "google_project_iam_binding" "role-binding" {
  project = var.project_id
  role    = google_project_iam_custom_role.custom-iam-role.name
  members = concat(
    [for user_member in var.user_members : "user:${user_member}"],
    [for service_account_member in var.service_account_members : "serviceAccount:${service_account_member}"]
  )
}
