output "redis_internal_ip" {
  description = "Internal IP address of the Redis instance."
  value       = module.redis.internal_ip
}

output "service_account_uris" {
  description = "Full URIs of the per-service service accounts, keyed by service name."
  value       = { for service, account in module.service-service-account : service => account.account_uri }
}

output "component_cloud_run_names" {
  description = "Deployed Cloud Run names for every service component, keyed by \"<service>-<component type>-<component name>\" with hyphens throughout."
  value = merge(
    { for key, config in local.servers : "${config.service_name}-server-${replace(config.server_name, "_", "-")}" => module.cloud-run-service-server[key].cloud_run_name },
    { for key, config in local.listeners : "${config.service_name}-listener-${replace(config.listener_name, "_", "-")}" => module.cloud-run-service-listener[key].cloud_run_name },
    { for key, config in local.executors : "${config.service_name}-executor-${replace(config.command_name, "_", "-")}" => module.cloud-run-service-executor[key].cloud_run_name },
    { for key, config in local.jobs : "${config.service_name}-job-${replace(config.job_name, "_", "-")}" => module.cloud-run-service-job[key].job_name },
    { for key, config in local.triggers : "${config.service_name}-trigger-${replace(config.trigger_name, "_", "-")}" => module.cloud-run-service-trigger[key].cloud_run_name },
  )
}
