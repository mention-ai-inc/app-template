output "api_url" {
  description = "Base URL of the API. One Front Door endpoint fronts every service, routing /rest/<service>/* to that service's Container App, so the URL shape main's web, mobile, and MCP clients build is unchanged."
  value       = module.front-door.api_url
}

output "api_fqdn" {
  description = "Hostname of the API."
  value       = module.front-door.api_fqdn
}

output "front_door_endpoint_host_name" {
  description = "Front Door's own endpoint hostname, which serves the same routes before the custom domain finishes validating."
  value       = module.front-door.endpoint_host_name
}

output "redis_hostname" {
  description = "Hostname of the cache."
  value       = module.redis.hostname
}

output "redis_ssl_port" {
  description = "TLS port of the cache."
  value       = module.redis.ssl_port
}

output "redis_password_secret_id" {
  description = "Versionless Key Vault URI of the cache's access key."
  value       = azurerm_key_vault_secret.redis-password.versionless_id
}

output "cosmos_database_name" {
  description = "Name of the Cosmos DB SQL database that holds every service's container in this environment."
  value       = azurerm_cosmosdb_sql_database.services.name
}

output "service_identity_ids" {
  description = "Resource IDs of the per-service user-assigned managed identities, keyed by service name."
  value       = { for service, identity in module.service-identity : service => identity.id }
}

output "service_identity_principal_ids" {
  description = "Object IDs of the per-service user-assigned managed identities, keyed by service name."
  value       = { for service, identity in module.service-identity : service => identity.principal_id }
}

output "deployable_components" {
  description = "Everything `m deploy-<service>` ships, keyed by \"<service>-<component type>-<component name>\" with hyphens throughout. Each entry names the Container Apps resource, whether it is a service or a job, and the console script that is its entrypoint. The field is called cloud_run_name because the CLI on main reads it by that name on every cloud."
  value = merge(
    { for key, config in local.servers : "${config.service_name}-server-${replace(config.server_name, "_", "-")}" => {
      cloud_run_name = module.container-app-server[key].container_app_name
      command        = "run-server-${replace(config.server_name, "_", "-")}"
      kind           = "service"
    } },
    { for key, config in local.pools : "${config.service_name}-pool-${replace(config.pool_name, "_", "-")}" => {
      cloud_run_name = module.container-app-pool[key].container_app_name
      command        = "run-pool-${config.component_type}s"
      kind           = "service"
    } },
    { for key, config in local.jobs : "${config.service_name}-job-${replace(config.job_name, "_", "-")}" => {
      cloud_run_name = module.container-app-job[key].job_name
      command        = "run-job-${replace(config.job_name, "_", "-")}"
      kind           = "job"
    } },
  )
}
