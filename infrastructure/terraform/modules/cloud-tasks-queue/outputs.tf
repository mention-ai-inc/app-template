output "queue_name" {
  description = "The short name of the Cloud Tasks queue created for this command."
  value       = google_cloud_tasks_queue.queue.name
}
