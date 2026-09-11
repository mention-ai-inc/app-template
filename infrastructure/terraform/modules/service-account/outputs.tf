output "email" {
  description = "Email address of the service account."
  value       = google_service_account.service-account.email
}

output "account_id" {
  description = "Username portion of the service account email address."
  value       = google_service_account.service-account.account_id
}

output "account_uri" {
  description = "The full URI of the service account."
  value       = google_service_account.service-account.name
}
