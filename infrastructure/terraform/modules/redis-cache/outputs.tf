output "hostname" {
  description = "Hostname clients connect to."
  value       = azurerm_redis_cache.cache.hostname
}

output "ssl_port" {
  description = "TLS port clients connect on."
  value       = azurerm_redis_cache.cache.ssl_port
}

output "primary_access_key" {
  description = "Access key clients authenticate with. Written to Key Vault rather than injected directly."
  value       = azurerm_redis_cache.cache.primary_access_key
  sensitive   = true
}

output "id" {
  description = "Resource ID of the cache, which is the scope a metric alert is raised against."
  value       = azurerm_redis_cache.cache.id
}
