output "cloud_run_name" {
  description = "The name of the deployed Cloud Run service."
  value       = google_cloud_run_v2_service.pool.name
}

output "uri" {
  description = "The base URL of the deployed Cloud Run service, which every entrypoint in the pool is routed under."
  value       = google_cloud_run_v2_service.pool.uri
}
