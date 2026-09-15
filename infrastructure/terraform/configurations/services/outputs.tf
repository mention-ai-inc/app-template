output "redis_internal_ip" {
  description = "Endpoint clients reach the cache at. Named for the field the GCP estate exposes so that the admin configuration reads the same key on every provider."
  value       = module.cache.primary_endpoint
}

output "redis_port" {
  description = "Port the cache listens on."
  value       = module.cache.port
}

output "dynamodb_table_name" {
  description = "The document store every service namespaces its partition keys inside."
  value       = module.document-store.table_name
}

output "dynamodb_table_stream_arn" {
  description = "The document store's change stream, which triggers read."
  value       = module.document-store.stream_arn
}

output "deployable_components" {
  description = "Everything `m deploy-<service>` ships, keyed by \"<service>-<component type>-<component name>\" with hyphens throughout. Each entry names the ECS resource, whether it is a long-running service or a job, and the console script that is its entrypoint. The field is called cloud_run_name on every provider because the deployment CLI on the base branch reads it by that name."
  value = merge(
    { for key, config in local.servers : "${config.service_name}-server-${replace(config.server_name, "_", "-")}" => {
      cloud_run_name = module.ecs-server[key].cloud_run_name
      command        = "run-server-${replace(config.server_name, "_", "-")}"
      kind           = "service"
    } },
    { for key, config in local.pools : "${config.service_name}-pool-${replace(config.pool_name, "_", "-")}" => {
      cloud_run_name = module.ecs-pool[key].cloud_run_name
      command        = "run-pool-${config.component_type}s"
      kind           = "service"
    } },
    { for key, config in local.jobs : "${config.service_name}-job-${replace(config.job_name, "_", "-")}" => {
      cloud_run_name = module.ecs-job[key].job_name
      command        = "run-job-${replace(config.job_name, "_", "-")}"
      kind           = "job"
    } },
  )
}
