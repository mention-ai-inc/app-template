locals {
  env_variables = {
    "CLERK_JWKS_URL" = module.environment.settings.tokens.clerk_jwks_url
    # config
    "GOOGLE_CLOUD_PROJECT" = local.project
    "FEATURE_ENVIRONMENT"  = local.feature_environment
    "PYTHONWARNINGS"       = var.python_warnings
    "REDIS_HOST"           = module.redis.internal_ip
    # secrets
    "REDIS_PASSWORD"      = data.google_secret_manager_secret_version_access.redis_password.secret_data
    "CLERK_SECRET_KEY"    = data.google_secret_manager_secret_version_access.clerk-secret-key.secret_data
    "GEMINI_API_KEY"      = data.google_secret_manager_secret_version_access.gemini-api-key.secret_data
    "SENTRY_DSN"          = var.enable_sentry ? data.google_secret_manager_secret_version_access.sentry-dsn[0].secret_data : ""
    "LOGFIRE_WRITE_TOKEN" = var.enable_logfire ? data.google_secret_manager_secret_version_access.logfire-write-token[0].secret_data : ""
  }
  servers = merge([
    for service_name, components in var.services : {
      for server_name, server_config in lookup(components, "servers", {}) : "${service_name}-${server_name}" => {
        service_name          = service_name
        server_name           = server_name
        cpu                   = lookup(server_config, "cpu", "1")
        memory                = lookup(server_config, "memory", "1Gi")
        container_concurrency = lookup(server_config, "container_concurrency", 80)
        timeout_seconds       = lookup(server_config, "timeout_seconds", 30)
        minimum_instances     = lookup(server_config, "minimum_instances", 0)
        maximum_instances     = lookup(server_config, "maximum_instances", 100)
        gunicorn_workers      = lookup(server_config, "gunicorn_workers", "1")
      }
  }]...)
  executor_pools = merge([
    for service_name, components in var.services : {
      for pool_name, pool_config in lookup(components, "executor_pools", {}) : "${service_name}-${pool_name}" => {
        service_name          = service_name
        pool_name             = pool_name
        component_type        = "executor"
        cpu                   = lookup(pool_config, "cpu", "1")
        memory                = lookup(pool_config, "memory", "1Gi")
        container_concurrency = lookup(pool_config, "container_concurrency", 80)
        timeout_seconds       = lookup(pool_config, "timeout_seconds", 300)
        minimum_instances     = local.is_production ? lookup(pool_config, "minimum_instances", 0) : 0
        maximum_instances     = lookup(pool_config, "maximum_instances", 100)
        gunicorn_workers      = lookup(pool_config, "gunicorn_workers", "1")
      }
  }]...)
  listener_pools = {
    for service_name, components in var.services : "${service_name}-listeners" => {
      service_name          = service_name
      pool_name             = "listeners"
      component_type        = "listener"
      cpu                   = lookup(lookup(components, "listener_pool", {}), "cpu", "1")
      memory                = lookup(lookup(components, "listener_pool", {}), "memory", "1Gi")
      container_concurrency = lookup(lookup(components, "listener_pool", {}), "container_concurrency", 80)
      timeout_seconds = lookup(lookup(components, "listener_pool", {}), "timeout_seconds", max([
        for listener_config in values(lookup(components, "listeners", {})) : lookup(listener_config, "timeout_seconds", 10)
      ]...))
      minimum_instances = local.is_production ? lookup(lookup(components, "listener_pool", {}), "minimum_instances", 0) : 0
      maximum_instances = lookup(lookup(components, "listener_pool", {}), "maximum_instances", 100)
      gunicorn_workers  = lookup(lookup(components, "listener_pool", {}), "gunicorn_workers", "1")
    } if length(lookup(components, "listeners", {})) > 0
  }
  trigger_pools = {
    for service_name, components in var.services : "${service_name}-triggers" => {
      service_name          = service_name
      pool_name             = "triggers"
      component_type        = "trigger"
      cpu                   = lookup(lookup(components, "trigger_pool", {}), "cpu", "1")
      memory                = lookup(lookup(components, "trigger_pool", {}), "memory", "1Gi")
      container_concurrency = lookup(lookup(components, "trigger_pool", {}), "container_concurrency", 80)
      timeout_seconds = lookup(lookup(components, "trigger_pool", {}), "timeout_seconds", max([
        for trigger_config in values(lookup(components, "triggers", {})) : lookup(trigger_config, "timeout_seconds", 60)
      ]...))
      minimum_instances = local.is_production ? lookup(lookup(components, "trigger_pool", {}), "minimum_instances", 0) : 0
      maximum_instances = lookup(lookup(components, "trigger_pool", {}), "maximum_instances", 100)
      gunicorn_workers  = lookup(lookup(components, "trigger_pool", {}), "gunicorn_workers", "1")
    } if length(lookup(components, "triggers", {})) > 0
  }
  pools = merge(local.executor_pools, local.listener_pools, local.trigger_pools)
  listeners = merge([
    for service_name, components in var.services : {
      for listener_name, listener_config in lookup(components, "listeners", {}) : "${service_name}-${listener_name}" => {
        service_name          = service_name
        listener_name         = listener_name
        subscriptions         = listener_config.subscriptions
        timeout_seconds       = lookup(listener_config, "timeout_seconds", 10)
        max_delivery_attempts = lookup(listener_config, "max_delivery_attempts", 5)
      }
  }]...)
  executors = merge([
    for service_name, components in var.services : {
      for executor_name, executor_config in lookup(components, "executors", {}) : "${service_name}-${executor_name}" => {
        service_name            = service_name
        command_name            = executor_name # executor is named exactly after the command it executes
        pool                    = executor_config.pool
        task_concurrency        = lookup(executor_config, "task_concurrency", 80)
        max_tasks_per_second    = lookup(executor_config, "max_tasks_per_second", 50)
        max_task_attempts       = lookup(executor_config, "max_task_attempts", 5)
        minimum_backoff_seconds = lookup(executor_config, "minimum_backoff_seconds", 5)
        maximum_backoff_seconds = lookup(executor_config, "maximum_backoff_seconds", 3600)
        maximum_doublings       = lookup(executor_config, "maximum_doublings", 16)
      }
  }]...)
  workers = merge([
    for service_name, components in var.services : {
      for worker_name, worker_config in lookup(components, "workers", {}) : "${service_name}-${worker_name}" => {
        service_name      = service_name
        worker_name       = worker_name
        command           = ["bash", "-c", "run-worker-${worker_name} || exit 0"]
        machine_type      = lookup(worker_config, "machine_type", "e2-small")
        minimum_instances = lookup(worker_config, "minimum_instances", 0)
        maximum_instances = lookup(worker_config, "maximum_instances", 1)
        spot_instance     = lookup(worker_config, "spot_instance", false)
        needs_external_ip = lookup(worker_config, "needs_external_ip", false)
      }
  }]...)
  jobs = merge([
    for service_name, components in var.services : {
      for job_name, job_config in lookup(components, "jobs", {}) : "${service_name}-${job_name}" => {
        service_name = service_name
        job_name     = job_name
        parallelism  = lookup(job_config, "parallelism", 1)
        task_count   = lookup(job_config, "task_count", 1)
        max_retries  = lookup(job_config, "max_retries", 0)
        cpu          = lookup(job_config, "cpu", "1")
        memory       = lookup(job_config, "memory", "1Gi")
        schedule     = lookup(job_config, "schedule", "")
      }
  }]...)
  triggers = merge([
    for service_name, components in var.services : {
      for trigger_name, trigger_config in lookup(components, "triggers", {}) : "${service_name}-${trigger_name}" => {
        service_name         = service_name
        trigger_name         = trigger_name
        firestore_collection = trigger_config.firestore_collection
        firestore_event_type = trigger_config.firestore_event_type
      }
  }]...)
  queue_names_json = jsonencode({
    for k, v in module.cloud-tasks-queue :
    "${local.executors[k].service_name}:${local.executors[k].command_name}" => v.queue_name
  })
  executor_pools_json = jsonencode({
    for k, v in local.executors :
    "${v.service_name}:${v.command_name}" => local.executor_pools["${v.service_name}-${v.pool}"].pool_name
  })
  routing_env = {
    "CLOUD_TASKS_QUEUES_JSON" = local.queue_names_json,
    "EXECUTOR_POOLS_JSON"     = local.executor_pools_json,
  }
}

module "cloud-run-service-server" {
  source   = "../../modules/cloud-run-server"
  for_each = local.servers

  project_id            = local.project
  region                = var.preferred_region
  feature_environment   = local.feature_environment
  service_name          = each.value.service_name
  server_name           = each.value.server_name
  service_account_email = module.service-service-account[each.value.service_name].email

  cpu                   = each.value.cpu
  memory                = each.value.memory
  container_concurrency = each.value.container_concurrency
  timeout_seconds       = each.value.timeout_seconds
  minimum_instances     = each.value.minimum_instances
  maximum_instances     = each.value.maximum_instances
  vpc_network           = data.terraform_remote_state.operations.outputs.shared-vpc-network-id
  vpc_subnetwork        = data.terraform_remote_state.operations.outputs.cloud-run-subnetwork-id
  env = merge(
    local.env_variables,
    local.routing_env,
    {
      "GUNICORN_TIMEOUT" = each.value.timeout_seconds,
      "GUNICORN_WORKERS" = each.value.gunicorn_workers,
    }
  )
}

module "cloud-run-pool" {
  source   = "../../modules/cloud-run-pool"
  for_each = local.pools

  project_id          = local.project
  region              = var.preferred_region
  feature_environment = local.feature_environment
  service_name        = each.value.service_name
  pool_name           = each.value.pool_name
  component_type      = each.value.component_type

  service_account_email = module.service-service-account[each.value.service_name].email
  container_concurrency = each.value.container_concurrency
  timeout_seconds       = each.value.timeout_seconds
  minimum_instances     = each.value.minimum_instances
  maximum_instances     = each.value.maximum_instances
  cpu                   = each.value.cpu
  memory                = each.value.memory
  vpc_network           = data.terraform_remote_state.operations.outputs.shared-vpc-network-id
  vpc_subnetwork        = data.terraform_remote_state.operations.outputs.cloud-run-subnetwork-id
  env = merge(
    local.env_variables,
    local.routing_env,
    {
      "GUNICORN_TIMEOUT" = each.value.timeout_seconds,
      "GUNICORN_WORKERS" = each.value.gunicorn_workers,
    }
  )
}

module "cloud-tasks-queue" {
  source   = "../../modules/cloud-tasks-queue"
  for_each = local.executors

  project_id          = local.project
  region              = var.preferred_region
  feature_environment = local.feature_environment
  service_name        = each.value.service_name
  command_name        = each.value.command_name

  task_concurrency        = each.value.task_concurrency
  max_tasks_per_second    = each.value.max_tasks_per_second
  max_task_attempts       = each.value.max_task_attempts
  minimum_backoff_seconds = each.value.minimum_backoff_seconds
  maximum_backoff_seconds = each.value.maximum_backoff_seconds
  maximum_doublings       = each.value.maximum_doublings
}

module "pubsub-listener-subscription" {
  source   = "../../modules/pubsub-listener-subscription"
  for_each = local.listeners

  project_id          = local.project
  project_number      = local.project_number
  feature_environment = local.feature_environment
  service_name        = each.value.service_name
  listener_name       = each.value.listener_name

  subscriptions         = each.value.subscriptions
  push_base_uri         = module.cloud-run-pool["${each.value.service_name}-listeners"].uri
  service_account_email = module.service-service-account[each.value.service_name].email
  timeout_seconds       = each.value.timeout_seconds
  max_delivery_attempts = each.value.max_delivery_attempts

  depends_on = [module.pubsub-topics] # topic names are passed as strings, so no explicit dependency on the module
}

module "compute-engine-service-worker" {
  source   = "../../modules/compute-engine-worker"
  for_each = local.workers

  project_id          = local.project
  region              = var.preferred_region
  zone                = local.instance_zone
  feature_environment = local.feature_environment
  service_name        = each.value.service_name
  worker_name         = each.value.worker_name
  command             = each.value.command
  image_uri           = "us-central1-docker.pkg.dev/${local.project}/${local.feature_environment}services/${each.value.service_name}:main"

  service_account_email = module.service-service-account[each.value.service_name].email
  subnetwork            = data.terraform_remote_state.operations.outputs.instances-subnetwork-id
  machine_type          = each.value.machine_type
  minimum_instances     = each.value.minimum_instances
  maximum_instances     = each.value.maximum_instances
  spot_instance         = each.value.spot_instance
  needs_external_ip     = each.value.needs_external_ip
  env                   = merge(local.env_variables, local.routing_env)

  depends_on = [module.pubsub-topics] # topic names are passed as strings, so no explicit dependency on the module
}

module "cloud-run-service-job" {
  source   = "../../modules/cloud-run-job"
  for_each = local.jobs

  project_id          = local.project
  project_number      = local.project_number
  region              = var.preferred_region
  feature_environment = local.feature_environment
  service_name        = each.value.service_name
  job_name            = each.value.job_name

  parallelism           = each.value.parallelism
  task_count            = each.value.task_count
  max_retries           = each.value.max_retries
  service_account_email = module.service-service-account[each.value.service_name].email
  cpu                   = each.value.cpu
  memory                = each.value.memory
  vpc_network           = data.terraform_remote_state.operations.outputs.shared-vpc-network-id
  vpc_subnetwork        = data.terraform_remote_state.operations.outputs.cloud-run-subnetwork-id
  schedule              = each.value.schedule
  env                   = merge(local.env_variables, local.routing_env)
}

module "eventarc-trigger" {
  source   = "../../modules/eventarc-trigger"
  for_each = local.triggers

  project_id          = local.project
  region              = var.preferred_region
  feature_environment = local.feature_environment
  service_name        = each.value.service_name
  trigger_name        = each.value.trigger_name

  firestore_collection  = each.value.firestore_collection
  firestore_event_type  = each.value.firestore_event_type
  pool_cloud_run_name   = module.cloud-run-pool["${each.value.service_name}-triggers"].cloud_run_name
  service_account_email = module.service-service-account[each.value.service_name].email
}
