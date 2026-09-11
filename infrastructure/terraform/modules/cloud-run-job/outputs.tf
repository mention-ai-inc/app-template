output "job_name" {
  description = "The name of the Cloud Run job."
  value       = google_cloud_run_v2_job.cloud-run-service-job.name
}
