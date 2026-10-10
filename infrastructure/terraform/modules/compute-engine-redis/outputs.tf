output "instance_name" {
  description = "The name of the Redis instance"
  value       = google_compute_instance.cache.name
}

output "instance_zone" {
  description = "The zone of the Redis instance"
  value       = google_compute_instance.cache.zone
}

output "internal_ip" {
  description = "The internal IP address of the Redis instance"
  value       = google_compute_instance.cache.network_interface[0].network_ip
}

output "external_ip" {
  description = "The external IP address of the Redis instance (if assigned)"
  value       = length(google_compute_instance.cache.network_interface[0].access_config) > 0 ? google_compute_instance.cache.network_interface[0].access_config[0].nat_ip : null
}

output "data_disk_name" {
  description = "The name of the Redis data disk"
  value       = google_compute_disk.redis_data.name
}

output "data_disk_size" {
  description = "The size of the Redis data disk in GB"
  value       = google_compute_disk.redis_data.size
}
