output "api_fqdn" {
  description = "The single hostname every service's REST routes are served under."
  value       = local.api_fqdn
}

output "api_url" {
  description = "The base URL of the API. Every backend route lives under /rest/<service>/, which is the shape the web, mobile, and MCP clients build."
  value       = "https://${local.api_fqdn}"
}

output "endpoint_host_name" {
  description = "The Front Door endpoint's own hostname, which serves the same routes before the custom domain finishes validating."
  value       = azurerm_cdn_frontdoor_endpoint.api.host_name
}

output "catchall_container_app_name" {
  description = "The name of the catchall Container App that absorbs requests matching no service route."
  value       = module.catchall-server.container_app_name
}
