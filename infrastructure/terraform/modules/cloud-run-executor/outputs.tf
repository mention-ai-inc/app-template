output "cloud_run_name" {
  description = "The name of the deployed Cloud Run service."
  value       = google_cloud_run_v2_service.executor.name
}

output "queue_name" {
  description = "The short name of the Cloud Tasks queue created for this executor."
  value       = google_cloud_tasks_queue.queue.name
}
