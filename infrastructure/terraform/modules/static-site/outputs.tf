output "bucket_name" {
  description = "Name of the Cloud Storage bucket"
  value       = google_storage_bucket.site.name
}

output "bucket_url" {
  description = "URL of the Cloud Storage bucket"
  value       = google_storage_bucket.site.url
}

output "load_balancer_ip" {
  description = "IP address of the load balancer"
  value       = google_compute_global_address.global_ip.address
}

output "domains" {
  description = "All domains configured for this static site"
  value       = local.all_domains
}

output "ssl_certificate_id" {
  description = "ID of the SSL certificate"
  value       = google_certificate_manager_certificate.ssl_certificate.id
}

output "ssl_certificate_status" {
  description = "Status of the SSL certificate"
  value       = google_certificate_manager_certificate.ssl_certificate.managed[0].state
}

output "site_urls" {
  description = "HTTPS URLs for all configured domains"
  value       = [for domain in local.all_domains : "https://${domain}"]
}

output "backend_bucket_name" {
  description = "Name of the backend bucket resource"
  value       = google_compute_backend_bucket.backend.name
}

output "url_map_name" {
  description = "Name of the URL map resource"
  value       = google_compute_url_map.url_map.name
}

output "dns_records" {
  description = "DNS A records created (if manage_dns is enabled)"
  value       = { for k, v in google_dns_record_set.domain_records : k => v.name }
}

output "uploaded_files_count" {
  description = "Number of files uploaded to the bucket"
  value       = length(local.site_files)
}

output "clean_url_mappings" {
  description = "Clean URL mappings configured"
  value       = var.clean_url_mappings
} 