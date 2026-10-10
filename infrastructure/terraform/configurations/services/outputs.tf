output "redis_internal_ip" {
  description = "Internal IP address of the Redis instance."
  value       = module.redis.internal_ip
}

output "service_account_uris" {
  description = "Full URIs of the per-service service accounts, keyed by service name."
  value       = { for service, account in module.service-service-account : service => account.account_uri }
}

output "deployable_components" {
  description = "Everything `m deploy-<service>` ships, keyed by \"<service>-<component type>-<component name>\" with hyphens throughout. Each entry names the Cloud Run resource, whether it is a service or a job, and the console script that is its entrypoint."
  value = merge(
    { for key, config in local.servers : "${config.service_name}-server-${replace(config.server_name, "_", "-")}" => {
      cloud_run_name = module.cloud-run-service-server[key].cloud_run_name
      command        = "run-server-${replace(config.server_name, "_", "-")}"
      kind           = "service"
    } },
    { for key, config in local.pools : "${config.service_name}-pool-${replace(config.pool_name, "_", "-")}" => {
      cloud_run_name = module.cloud-run-pool[key].cloud_run_name
      command        = "run-pool-${config.component_type}s"
      kind           = "service"
    } },
    { for key, config in local.jobs : "${config.service_name}-job-${replace(config.job_name, "_", "-")}" => {
      cloud_run_name = module.cloud-run-service-job[key].job_name
      command        = "run-job-${replace(config.job_name, "_", "-")}"
      kind           = "job"
    } },
  )
}
