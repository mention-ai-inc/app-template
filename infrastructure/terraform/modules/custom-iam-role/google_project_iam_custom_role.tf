resource "google_project_iam_custom_role" "custom-iam-role" {
  project     = var.project_id
  role_id     = "${var.role_id}_${random_string.role_suffix.result}"
  title       = var.title
  description = var.description
  permissions = var.permissions
}

resource "random_string" "role_suffix" {
  length  = 4
  special = false
  upper   = false
}
