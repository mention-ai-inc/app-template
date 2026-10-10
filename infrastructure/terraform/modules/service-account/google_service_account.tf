resource "google_service_account" "service-account" {
  project                      = var.project_id
  account_id                   = var.account_id
  display_name                 = "${var.account_id} Service Account"
  create_ignore_already_exists = true
}
