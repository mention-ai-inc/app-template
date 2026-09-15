locals {
  env_variables = {
    "AZURE_SUBSCRIPTION_ID" = var.subscription_id
    "AZURE_RESOURCE_GROUP"  = local.resource_group_name
    "FEATURE_ENVIRONMENT"   = local.feature_environment
    "PYTHONWARNINGS"        = var.python_warnings
    "AZURE_KEY_VAULT_URI"   = local.key_vault_uri
    "AZURE_REGION"          = var.preferred_region
    "COSMOS_ENDPOINT"       = local.cosmos_endpoint
    "COSMOS_DATABASE"       = azurerm_cosmosdb_sql_database.services.name
    "SERVICE_BUS_NAMESPACE" = local.servicebus_namespace_host
    "BLOB_ACCOUNT_URL"      = "https://${local.storage_account_name}.blob.core.windows.net"
    "REDIS_HOST"            = module.redis.hostname
    "REDIS_PORT"            = tostring(module.redis.ssl_port)
    "REDIS_SSL"             = "true"
  }

  servers = merge([
    for service_name, components in var.services : {
      for server_name, server_config in lookup(components, "servers", {}) : "${service_name}-${server_name}" => {
        service_name          = service_name
        server_name           = server_name
        cpu                   = lookup(server_config, "cpu", 0.5)
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
        cpu                   = lookup(pool_config, "cpu", 0.5)
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
      cpu                   = lookup(lookup(components, "listener_pool", {}), "cpu", 0.5)
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
      cpu                   = lookup(lookup(components, "trigger_pool", {}), "cpu", 0.5)
      memory                = lookup(lookup(components, "trigger_pool", {}), "memory", "1Gi")
      container_concurrency = lookup(lookup(components, "trigger_pool", {}), "container_concurrency", 80)
      timeout_seconds = lookup(lookup(components, "trigger_pool", {}), "timeout_seconds", max([
        for trigger_config in values(lookup(components, "triggers", {})) : lookup(trigger_config, "timeout_seconds", 60)
      ]...))
      minimum_instances = max(lookup(lookup(components, "trigger_pool", {}), "minimum_instances", 1), 1)
      maximum_instances = lookup(lookup(components, "trigger_pool", {}), "maximum_instances", 1)
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
        service_name          = service_name
        command_name          = executor_name
        pool                  = executor_config.pool
        task_concurrency      = lookup(executor_config, "task_concurrency", 80)
        max_task_attempts     = lookup(executor_config, "max_task_attempts", 5)
        lock_duration_seconds = lookup(executor_config, "lock_duration_seconds", 300)
      }
  }]...)

  jobs = merge([
    for service_name, components in var.services : {
      for job_name, job_config in lookup(components, "jobs", {}) : "${service_name}-${job_name}" => {
        service_name         = service_name
        job_name             = job_name
        parallelism          = lookup(job_config, "parallelism", 1)
        task_count           = lookup(job_config, "task_count", 1)
        max_retries          = lookup(job_config, "max_retries", 0)
        task_timeout_seconds = lookup(job_config, "task_timeout_seconds", 600)
        cpu                  = lookup(job_config, "cpu", 0.5)
        memory               = lookup(job_config, "memory", "1Gi")
        schedule             = lookup(job_config, "schedule", "")
      }
  }]...)

  triggers = merge([
    for service_name, components in var.services : {
      for trigger_name, trigger_config in lookup(components, "triggers", {}) : "${service_name}-${trigger_name}" => {
        service_name  = service_name
        trigger_name  = trigger_name
        document_type = trigger_config.document_type
      }
  }]...)

  queue_names = {
    for key, config in local.executors :
    key => "${local.feature_environment}${config.service_name}-${replace(config.command_name, "_", "-")}"
  }

  listener_subscriptions = merge([
    for key, config in local.listeners : {
      for index, subscription in config.subscriptions : "${key}-${index}" => {
        service_name      = config.service_name
        listener_name     = config.listener_name
        topic_name        = "${local.feature_environment}${subscription.topic_name}"
        subscription_name = "${local.feature_environment}${config.service_name}-${replace(config.listener_name, "_", "-")}-${index}"
      }
    }
  ]...)

  executor_pool_scale_rules = {
    for pool_key, pool_config in local.executor_pools : pool_key => [
      for executor_key, executor_config in local.executors : {
        name          = replace(executor_key, "_", "-")
        queue_name    = local.queue_names[executor_key]
        message_count = executor_config.task_concurrency
      }
      if "${executor_config.service_name}-${executor_config.pool}" == pool_key
    ]
  }

  listener_pool_scale_rules = {
    for pool_key, pool_config in local.listener_pools : pool_key => [
      for subscription_key, subscription in local.listener_subscriptions : {
        name              = replace(subscription_key, "_", "-")
        topic_name        = subscription.topic_name
        subscription_name = subscription.subscription_name
        message_count     = pool_config.container_concurrency
      }
      if subscription.service_name == pool_config.service_name
    ]
  }

  queue_names_json = jsonencode({
    for key, name in local.queue_names :
    "${local.executors[key].service_name}:${local.executors[key].command_name}" => name
  })

  executor_pools_json = jsonencode({
    for key, config in local.executors :
    "${config.service_name}:${config.command_name}" => local.executor_pools["${config.service_name}-${config.pool}"].pool_name
  })

  change_feed_triggers_json = jsonencode({
    for key, config in local.triggers :
    "${config.service_name}:${config.trigger_name}" => module.cosmos-change-feed-trigger[key].routing
  })

  listener_subscriptions_json = jsonencode({
    for key, config in local.listeners :
    "${config.service_name}:${config.listener_name}" => module.service-bus-listener-subscription[key].subscriptions
  })

  routing_env = {
    "SERVICE_BUS_QUEUES_JSON"        = local.queue_names_json,
    "SERVICE_BUS_SUBSCRIPTIONS_JSON" = local.listener_subscriptions_json,
    "EXECUTOR_POOLS_JSON"            = local.executor_pools_json,
    "CHANGE_FEED_TRIGGERS_JSON"      = local.change_feed_triggers_json,
  }
}

module "container-app-server" {
  source   = "../../modules/container-app-server"
  for_each = local.servers

  resource_group_name          = local.resource_group_name
  location                     = var.preferred_region
  container_app_environment_id = local.container_app_environment_id
  feature_environment          = local.feature_environment
  service_name                 = each.value.service_name
  server_name                  = each.value.server_name

  identity_id           = module.service-identity[each.value.service_name].id
  registry_login_server = local.registry_login_server
  image                 = "${local.image_repository}/${each.value.service_name}:main"

  cpu                   = each.value.cpu
  memory                = each.value.memory
  container_concurrency = each.value.container_concurrency
  timeout_seconds       = each.value.timeout_seconds
  minimum_instances     = each.value.minimum_instances
  maximum_instances     = each.value.maximum_instances

  secret_env = local.secret_env
  env = merge(
    local.env_variables,
    local.routing_env,
    {
      "AZURE_CLIENT_ID"     = module.service-identity[each.value.service_name].client_id,
      "AZURE_FRONT_DOOR_ID" = local.front_door_resource_guid,
      "GUNICORN_TIMEOUT"    = tostring(each.value.timeout_seconds),
      "GUNICORN_WORKERS"    = each.value.gunicorn_workers,
    }
  )
}

module "container-app-pool" {
  source   = "../../modules/container-app-pool"
  for_each = local.pools

  resource_group_name          = local.resource_group_name
  container_app_environment_id = local.container_app_environment_id
  feature_environment          = local.feature_environment
  service_name                 = each.value.service_name
  pool_name                    = each.value.pool_name
  component_type               = each.value.component_type

  identity_id           = module.service-identity[each.value.service_name].id
  registry_login_server = local.registry_login_server
  image                 = "${local.image_repository}/${each.value.service_name}:main"

  cpu               = each.value.cpu
  memory            = each.value.memory
  minimum_instances = each.value.minimum_instances
  maximum_instances = each.value.maximum_instances

  service_bus_namespace_name = local.servicebus_namespace_name
  queue_scale_rules          = lookup(local.executor_pool_scale_rules, each.key, [])
  subscription_scale_rules   = lookup(local.listener_pool_scale_rules, each.key, [])

  secret_env = local.secret_env
  env = merge(
    local.env_variables,
    local.routing_env,
    {
      "AZURE_CLIENT_ID"  = module.service-identity[each.value.service_name].client_id,
      "GUNICORN_TIMEOUT" = tostring(each.value.timeout_seconds),
      "GUNICORN_WORKERS" = each.value.gunicorn_workers,
    }
  )

  depends_on = [
    module.service-bus-queue,
    module.service-bus-listener-subscription,
  ]
}

module "service-bus-queue" {
  source   = "../../modules/service-bus-queue"
  for_each = local.executors

  namespace_id        = local.servicebus_namespace_id
  feature_environment = local.feature_environment
  service_name        = each.value.service_name
  command_name        = each.value.command_name

  max_task_attempts     = each.value.max_task_attempts
  lock_duration_seconds = each.value.lock_duration_seconds
}

module "service-bus-listener-subscription" {
  source   = "../../modules/service-bus-listener-subscription"
  for_each = local.listeners

  namespace_id        = local.servicebus_namespace_id
  feature_environment = local.feature_environment
  service_name        = each.value.service_name
  listener_name       = each.value.listener_name

  subscriptions         = each.value.subscriptions
  timeout_seconds       = each.value.timeout_seconds
  max_delivery_attempts = each.value.max_delivery_attempts

  depends_on = [module.service-bus-topics]
}

module "container-app-job" {
  source   = "../../modules/container-app-job"
  for_each = local.jobs

  resource_group_name          = local.resource_group_name
  location                     = var.preferred_region
  container_app_environment_id = local.container_app_environment_id
  feature_environment          = local.feature_environment
  service_name                 = each.value.service_name
  job_name                     = each.value.job_name

  identity_id           = module.service-identity[each.value.service_name].id
  registry_login_server = local.registry_login_server
  image                 = "${local.image_repository}/${each.value.service_name}:main"

  parallelism          = each.value.parallelism
  task_count           = each.value.task_count
  max_retries          = each.value.max_retries
  task_timeout_seconds = each.value.task_timeout_seconds
  cpu                  = each.value.cpu
  memory               = each.value.memory
  schedule             = each.value.schedule

  secret_env = local.secret_env
  env = merge(
    local.env_variables,
    local.routing_env,
    {
      "AZURE_CLIENT_ID" = module.service-identity[each.value.service_name].client_id,
    }
  )
}

module "cosmos-change-feed-trigger" {
  source   = "../../modules/cosmos-change-feed-trigger"
  for_each = local.triggers

  resource_group_name    = local.resource_group_name
  cosmos_account_name    = local.cosmos_account_name
  cosmos_database_name   = azurerm_cosmosdb_sql_database.services.name
  watched_container_name = azurerm_cosmosdb_sql_container.service[each.value.service_name].name
  service_name           = each.value.service_name
  trigger_name           = each.value.trigger_name
  document_type          = each.value.document_type

  provisioned_throughput = local.is_production
  max_throughput         = var.cosmos_lease_max_throughput
}
