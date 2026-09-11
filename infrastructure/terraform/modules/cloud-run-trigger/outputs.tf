output "cloud_run_name" {
  description = "The name of the deployed Cloud Run service."
  value       = google_cloud_run_v2_service.trigger.name
}
