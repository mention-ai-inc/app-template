resource "google_project_iam_member" "assigned-roles" {
  for_each = toset(var.roles)

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.service-account.email}"
}

resource "google_service_account_iam_member" "self-token-creation" {
  service_account_id = google_service_account.service-account.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:${google_service_account.service-account.email}"
}

resource "google_service_account_iam_member" "self-use" {
  service_account_id = google_service_account.service-account.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.service-account.email}"
}

resource "google_service_account_iam_member" "bind-service-accounts-to-service-account-as-user" {
  count = length(var.service_account_impersonaters)

  service_account_id = google_service_account.service-account.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${var.service_account_impersonaters[count.index]}"
}

resource "google_service_account_iam_member" "bind-user-accounts-to-service-account-as-user" {
  count = length(var.user_impersonaters)

  service_account_id = google_service_account.service-account.name
  role               = "roles/iam.serviceAccountUser"
  member             = "user:${var.user_impersonaters[count.index]}"
}

resource "google_service_account_iam_member" "bind-service-accounts-to-service-account-as-token-creator" {
  count = length(var.service_account_impersonaters)

  service_account_id = google_service_account.service-account.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:${var.service_account_impersonaters[count.index]}"
}

resource "google_service_account_iam_member" "bind-user-accounts-to-service-account-as-token-creator" {
  count = length(var.user_impersonaters)

  service_account_id = google_service_account.service-account.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "user:${var.user_impersonaters[count.index]}"
}
