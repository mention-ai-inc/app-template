data "google_iam_policy" "cloud-run-public-access" {
  binding {
    role = "roles/run.invoker"
    members = (
      var.public_access
      ? ["allUsers"]
      : ["serviceAccount:service-${var.project_number}@gcp-sa-iap.iam.gserviceaccount.com"]
    )
  }
}

resource "google_cloud_run_service_iam_policy" "cloud-run-public-access" {
  location = var.region
  project  = var.project_id
  service  = google_cloud_run_v2_service.service.name

  policy_data = data.google_iam_policy.cloud-run-public-access.policy_data
}
