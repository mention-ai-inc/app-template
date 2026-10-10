output "service_name" {
  description = "The name of the service being deployed."
  value       = var.service_name
}

output "cloud_run_name" {
  description = "The name of the deployed Cloud Run service."
  value       = google_cloud_run_v2_service.service.name
}

output "backend_service_self_link" {
  description = "The URI of the backend service."
  value       = google_compute_backend_service.backend-service.self_link
}

output "backend_service_id" {
  description = "The numeric identifier of the backend service, as used in the IAP JWT audience."
  value       = google_compute_backend_service.backend-service.generated_id
}

output "backend_service_name" {
  description = "The name of the backend service."
  value       = google_compute_backend_service.backend-service.name
}
