locals {
  env_variables = {
    # config
    "GOOGLE_CLOUD_PROJECT" = local.project
    "FEATURE_ENVIRONMENT"  = local.feature_environment
    "PYTHONWARNINGS"       = var.python_warnings
    "REDIS_HOST"           = module.redis.internal_ip
    # secrets
    "REDIS_PASSWORD"       = data.google_secret_manager_secret_version_access.redis_password.secret_data
    "CLERK_SECRET_KEY"     = data.google_secret_manager_secret_version_access.clerk-secret-key.secret_data
    "CLERK_WEBHOOK_SECRET" = data.google_secret_manager_secret_version_access.clerk-webhook-secret.secret_data
    "GEMINI_API_KEY"       = data.google_secret_manager_secret_version_access.gemini-api-key.secret_data
    "SENTRY_DSN"           = data.google_secret_manager_secret_version_access.sentry-dsn.secret_data
    "LOGFIRE_WRITE_TOKEN"  = data.google_secret_manager_secret_version_access.logfire-write-token.secret_data
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
  listeners = merge([
    for service_name, components in var.services : {
      for listener_name, listener_config in lookup(components, "listeners", {}) : "${service_name}-${listener_name}" => {
        service_name          = service_name
        listener_name         = listener_name
        subscriptions         = listener_config.subscriptions
        cpu                   = lookup(listener_config, "cpu", "1")
        memory                = lookup(listener_config, "memory", "1Gi")
        container_concurrency = lookup(listener_config, "container_concurrency", 80)
        timeout_seconds       = lookup(listener_config, "timeout_seconds", 10)
        minimum_instances     = lookup(listener_config, "minimum_instances", 0)
        maximum_instances     = lookup(listener_config, "maximum_instances", 100)
        gunicorn_workers      = lookup(listener_config, "gunicorn_workers", "1")
        max_delivery_attempts = lookup(listener_config, "max_delivery_attempts", 5)
      }
  }]...)
  executors = merge([
    for service_name, components in var.services : {
      for executor_name, executor_config in lookup(components, "executors", {}) : "${service_name}-${executor_name}" => {
        service_name            = service_name
        command_name            = executor_name # executor is named exactly after the command it executes
        cpu                     = lookup(executor_config, "cpu", "1")
        memory                  = lookup(executor_config, "memory", "1Gi")
        container_concurrency   = lookup(executor_config, "container_concurrency", 80)
        timeout_seconds         = lookup(executor_config, "timeout_seconds", 300)
        minimum_instances       = local.is_production ? lookup(executor_config, "minimum_instances", 0) : 0
        maximum_instances       = lookup(executor_config, "maximum_instances", 100)
        gunicorn_workers        = lookup(executor_config, "gunicorn_workers", "1")
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
        service_name          = service_name
        trigger_name          = trigger_name
        firestore_collection  = trigger_config.firestore_collection
        firestore_event_type  = trigger_config.firestore_event_type
        cpu                   = lookup(trigger_config, "cpu", "1")
        memory                = lookup(trigger_config, "memory", "1Gi")
        container_concurrency = lookup(trigger_config, "container_concurrency", 80)
        timeout_seconds       = lookup(trigger_config, "timeout_seconds", 60)
        minimum_instances     = lookup(trigger_config, "minimum_instances", 0)
        maximum_instances     = lookup(trigger_config, "maximum_instances", 100)
        gunicorn_workers      = lookup(trigger_config, "gunicorn_workers", "1")
      }
  }]...)
  queue_names_json = jsonencode({
    for k, v in module.cloud-run-service-executor :
    "${local.executors[k].service_name}:${local.executors[k].command_name}" => v.queue_name
  })
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
    {
      "GUNICORN_TIMEOUT"        = each.value.timeout_seconds,
      "GUNICORN_WORKERS"        = each.value.gunicorn_workers,
      "CLOUD_TASKS_QUEUES_JSON" = local.queue_names_json,
    }
  )
}

module "cloud-run-service-listener" {
  source   = "../../modules/cloud-run-listener"
  for_each = local.listeners

  project_id          = local.project
  project_number      = local.project_number
  region              = var.preferred_region
  feature_environment = local.feature_environment
  service_name        = each.value.service_name
  listener_name       = each.value.listener_name

  subscriptions = each.value.subscriptions

  service_account_email = module.service-service-account[each.value.service_name].email
  container_concurrency = each.value.container_concurrency
  timeout_seconds       = each.value.timeout_seconds
  minimum_instances     = each.value.minimum_instances
  maximum_instances     = each.value.maximum_instances
  cpu                   = each.value.cpu
  memory                = each.value.memory
  max_delivery_attempts = each.value.max_delivery_attempts
  vpc_network           = data.terraform_remote_state.operations.outputs.shared-vpc-network-id
  vpc_subnetwork        = data.terraform_remote_state.operations.outputs.cloud-run-subnetwork-id
  env = merge(
    local.env_variables,
    {
      "GUNICORN_TIMEOUT"        = each.value.timeout_seconds,
      "GUNICORN_WORKERS"        = each.value.gunicorn_workers,
      "CLOUD_TASKS_QUEUES_JSON" = local.queue_names_json,
    }
  )

  depends_on = [module.pubsub-topics] # topic names are passed as strings, so no explicit dependency on the module
}

module "cloud-run-service-executor" {
  source   = "../../modules/cloud-run-executor"
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
  service_account_email   = module.service-service-account[each.value.service_name].email
  container_concurrency   = each.value.container_concurrency
  timeout_seconds         = each.value.timeout_seconds
  minimum_instances       = each.value.minimum_instances
  maximum_instances       = each.value.maximum_instances
  cpu                     = each.value.cpu
  memory                  = each.value.memory
  vpc_network             = data.terraform_remote_state.operations.outputs.shared-vpc-network-id
  vpc_subnetwork          = data.terraform_remote_state.operations.outputs.cloud-run-subnetwork-id
  env = merge(
    local.env_variables,
    {
      "GUNICORN_TIMEOUT" = each.value.timeout_seconds,
      "GUNICORN_WORKERS" = each.value.gunicorn_workers
    }
  )
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
  env = merge(
    local.env_variables,
    {
      "CLOUD_TASKS_QUEUES_JSON" = local.queue_names_json,
    }
  )

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
  env = merge(
    local.env_variables,
    {
      "CLOUD_TASKS_QUEUES_JSON" = local.queue_names_json,
    }
  )
}

module "cloud-run-service-trigger" {
  source   = "../../modules/cloud-run-trigger"
  for_each = local.triggers

  project_id          = local.project
  project_number      = local.project_number
  region              = var.preferred_region
  feature_environment = local.feature_environment
  service_name        = each.value.service_name
  trigger_name        = each.value.trigger_name

  firestore_collection  = each.value.firestore_collection
  firestore_event_type  = each.value.firestore_event_type
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
    {
      "GUNICORN_TIMEOUT"        = each.value.timeout_seconds,
      "GUNICORN_WORKERS"        = each.value.gunicorn_workers,
      "CLOUD_TASKS_QUEUES_JSON" = local.queue_names_json,
    }
  )
}
