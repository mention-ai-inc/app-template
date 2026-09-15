locals {
  env_variables = {
    "AWS_REGION"                = var.preferred_region
    "AWS_ACCOUNT_ID"            = local.account_id
    "FEATURE_ENVIRONMENT"       = local.feature_environment
    "PYTHONWARNINGS"            = var.python_warnings
    "REDIS_HOST"                = module.cache.primary_endpoint
    "REDIS_PORT"                = tostring(module.cache.port)
    "REDIS_TLS"                 = "true"
    "DYNAMODB_TABLE_NAME"       = module.document-store.table_name
    "DYNAMODB_COLLECTION_INDEX" = module.document-store.collection_index_name
    "S3_BUCKET_PREFIX"          = local.bucket_name_prefix
    "EVENT_TOPIC_ARNS_JSON"     = jsonencode(local.topic_arns)
  }
  servers = merge([
    for service_name, components in var.services : {
      for server_name, server_config in lookup(components, "servers", {}) : "${service_name}-${server_name}" => {
        service_name          = service_name
        server_name           = server_name
        cpu                   = lookup(server_config, "cpu", "512")
        memory                = lookup(server_config, "memory", "1024")
        container_concurrency = lookup(server_config, "container_concurrency", 80)
        timeout_seconds       = lookup(server_config, "timeout_seconds", 30)
        minimum_instances     = local.is_production ? lookup(server_config, "minimum_instances", 2) : 1
        maximum_instances     = lookup(server_config, "maximum_instances", 100)
      }
  }]...)
  executor_pools = merge([
    for service_name, components in var.services : {
      for pool_name, pool_config in lookup(components, "executor_pools", {}) : "${service_name}-${pool_name}" => {
        service_name          = service_name
        pool_name             = pool_name
        component_type        = "executor"
        cpu                   = lookup(pool_config, "cpu", "512")
        memory                = lookup(pool_config, "memory", "1024")
        container_concurrency = lookup(pool_config, "container_concurrency", 80)
        timeout_seconds       = lookup(pool_config, "timeout_seconds", 300)
        minimum_instances     = local.is_production ? lookup(pool_config, "minimum_instances", 1) : 1
        maximum_instances     = lookup(pool_config, "maximum_instances", 100)
      }
  }]...)
  listener_pools = {
    for service_name, components in var.services : "${service_name}-listeners" => {
      service_name          = service_name
      pool_name             = "listeners"
      component_type        = "listener"
      cpu                   = lookup(lookup(components, "listener_pool", {}), "cpu", "512")
      memory                = lookup(lookup(components, "listener_pool", {}), "memory", "1024")
      container_concurrency = lookup(lookup(components, "listener_pool", {}), "container_concurrency", 80)
      timeout_seconds = lookup(lookup(components, "listener_pool", {}), "timeout_seconds", max([
        for listener_config in values(lookup(components, "listeners", {})) : lookup(listener_config, "timeout_seconds", 60)
      ]...))
      minimum_instances = local.is_production ? lookup(lookup(components, "listener_pool", {}), "minimum_instances", 1) : 1
      maximum_instances = lookup(lookup(components, "listener_pool", {}), "maximum_instances", 100)
    } if length(lookup(components, "listeners", {})) > 0
  }
  trigger_pools = {
    for service_name, components in var.services : "${service_name}-triggers" => {
      service_name          = service_name
      pool_name             = "triggers"
      component_type        = "trigger"
      cpu                   = lookup(lookup(components, "trigger_pool", {}), "cpu", "512")
      memory                = lookup(lookup(components, "trigger_pool", {}), "memory", "1024")
      container_concurrency = lookup(lookup(components, "trigger_pool", {}), "container_concurrency", 80)
      timeout_seconds = lookup(lookup(components, "trigger_pool", {}), "timeout_seconds", max([
        for trigger_config in values(lookup(components, "triggers", {})) : lookup(trigger_config, "timeout_seconds", 60)
      ]...))
      minimum_instances = local.is_production ? lookup(lookup(components, "trigger_pool", {}), "minimum_instances", 1) : 1
      maximum_instances = lookup(lookup(components, "trigger_pool", {}), "maximum_instances", 100)
    } if length(lookup(components, "triggers", {})) > 0
  }
  pools = merge(local.executor_pools, local.listener_pools, local.trigger_pools)
  listeners = merge([
    for service_name, components in var.services : {
      for listener_name, listener_config in lookup(components, "listeners", {}) : "${service_name}-${listener_name}" => {
        service_name          = service_name
        listener_name         = listener_name
        subscriptions         = listener_config.subscriptions
        timeout_seconds       = lookup(listener_config, "timeout_seconds", 60)
        max_delivery_attempts = lookup(listener_config, "max_delivery_attempts", 5)
      }
  }]...)
  executors = merge([
    for service_name, components in var.services : {
      for executor_name, executor_config in lookup(components, "executors", {}) : "${service_name}-${executor_name}" => {
        service_name               = service_name
        command_name               = executor_name
        pool                       = executor_config.pool
        task_concurrency           = lookup(executor_config, "task_concurrency", 80)
        max_task_attempts          = lookup(executor_config, "max_task_attempts", 5)
        visibility_timeout_seconds = lookup(executor_config, "visibility_timeout_seconds", 300)
      }
  }]...)
  jobs = merge([
    for service_name, components in var.services : {
      for job_name, job_config in lookup(components, "jobs", {}) : "${service_name}-${job_name}" => {
        service_name         = service_name
        job_name             = job_name
        task_count           = lookup(job_config, "task_count", 1)
        max_retries          = lookup(job_config, "max_retries", 0)
        task_timeout_seconds = lookup(job_config, "task_timeout_seconds", 3600)
        cpu                  = lookup(job_config, "cpu", "1024")
        memory               = lookup(job_config, "memory", "2048")
        schedule             = lookup(job_config, "schedule", "")
      }
  }]...)
  triggers = merge([
    for service_name, components in var.services : {
      for trigger_name, trigger_config in lookup(components, "triggers", {}) : "${service_name}-${trigger_name}" => {
        service_name    = service_name
        trigger_name    = trigger_name
        collection      = trigger_config.collection
        timeout_seconds = lookup(trigger_config, "timeout_seconds", 60)
      }
  }]...)
  executor_queues_json = jsonencode({
    for key, queue in module.sqs-executor-queue :
    "${local.executors[key].service_name}:${local.executors[key].command_name}" => queue.queue_url
  })
  executor_pools_json = jsonencode({
    for key, executor in local.executors :
    "${executor.service_name}:${executor.command_name}" => local.executor_pools["${executor.service_name}-${executor.pool}"].pool_name
  })
  listener_queues_json = jsonencode({
    for key, listener in module.sqs-listener-subscription :
    "${local.listeners[key].service_name}:${local.listeners[key].listener_name}" => listener.queue_urls
  })
  trigger_queues_json = jsonencode({
    for key, trigger in module.dynamodb-stream-trigger :
    "${local.triggers[key].service_name}:${local.triggers[key].trigger_name}" => trigger.queue_url
  })
  routing_env = {
    "SQS_EXECUTOR_QUEUES_JSON" = local.executor_queues_json
    "EXECUTOR_POOLS_JSON"      = local.executor_pools_json
    "SQS_LISTENER_QUEUES_JSON" = local.listener_queues_json
    "SQS_TRIGGER_QUEUES_JSON"  = local.trigger_queues_json
  }
  pool_backlog_queue_names = {
    for key, pool in local.pools : key => (
      pool.component_type == "executor" ? [
        for executor_key, executor in local.executors :
        module.sqs-executor-queue[executor_key].queue_name
        if executor.service_name == pool.service_name && executor.pool == pool.pool_name
        ] : pool.component_type == "listener" ? flatten([
          for listener_key, listener in local.listeners :
          module.sqs-listener-subscription[listener_key].queue_names
          if listener.service_name == pool.service_name
        ]) : [
        for trigger_key, trigger in local.triggers :
        module.dynamodb-stream-trigger[trigger_key].queue_name
        if trigger.service_name == pool.service_name
      ]
    )
  }
}

module "ecs-server" {
  source   = "../../modules/ecs-server"
  for_each = local.servers

  region              = var.preferred_region
  feature_environment = local.feature_environment
  cluster_arn         = local.cluster_arn
  cluster_name        = local.cluster_name
  service_name        = each.value.service_name
  server_name         = each.value.server_name

  task_role_arn      = module.service-task-role[each.value.service_name].arn
  execution_role_arn = module.task-execution-role.arn

  cpu                   = each.value.cpu
  memory                = each.value.memory
  container_concurrency = each.value.container_concurrency
  timeout_seconds       = each.value.timeout_seconds
  minimum_instances     = each.value.minimum_instances
  maximum_instances     = each.value.maximum_instances
  log_retention_days    = var.log_retention_days

  vpc_id                          = local.vpc_id
  subnet_ids                      = local.private_subnet_ids
  load_balancer_security_group_id = module.api-load-balancer.security_group_id

  env     = merge(local.env_variables, local.routing_env)
  secrets = local.secret_variables
}

module "ecs-pool" {
  source   = "../../modules/ecs-pool"
  for_each = local.pools

  region              = var.preferred_region
  feature_environment = local.feature_environment
  cluster_arn         = local.cluster_arn
  cluster_name        = local.cluster_name
  service_name        = each.value.service_name
  pool_name           = each.value.pool_name
  component_type      = each.value.component_type

  task_role_arn      = module.service-task-role[each.value.service_name].arn
  execution_role_arn = module.task-execution-role.arn

  cpu                   = each.value.cpu
  memory                = each.value.memory
  container_concurrency = each.value.container_concurrency
  timeout_seconds       = each.value.timeout_seconds
  minimum_instances     = each.value.minimum_instances
  maximum_instances     = each.value.maximum_instances
  backlog_queue_names   = local.pool_backlog_queue_names[each.key]
  log_retention_days    = var.log_retention_days

  vpc_id     = local.vpc_id
  subnet_ids = local.private_subnet_ids

  env     = merge(local.env_variables, local.routing_env)
  secrets = local.secret_variables
}

module "sqs-executor-queue" {
  source   = "../../modules/sqs-executor-queue"
  for_each = local.executors

  feature_environment = local.feature_environment
  service_name        = each.value.service_name
  command_name        = each.value.command_name

  task_concurrency           = each.value.task_concurrency
  max_task_attempts          = each.value.max_task_attempts
  visibility_timeout_seconds = each.value.visibility_timeout_seconds
  reader_writer_role_arns    = [for role in module.service-task-role : role.arn]
}

module "sqs-listener-subscription" {
  source   = "../../modules/sqs-listener-subscription"
  for_each = local.listeners

  feature_environment = local.feature_environment
  service_name        = each.value.service_name
  listener_name       = each.value.listener_name

  subscriptions         = each.value.subscriptions
  topic_arns            = local.topic_arns
  timeout_seconds       = each.value.timeout_seconds
  max_delivery_attempts = each.value.max_delivery_attempts
  reader_role_arns      = [module.service-task-role[each.value.service_name].arn]
}

module "dynamodb-stream-trigger" {
  source   = "../../modules/dynamodb-stream-trigger"
  for_each = local.triggers

  feature_environment = local.feature_environment
  service_name        = each.value.service_name
  trigger_name        = each.value.trigger_name

  collection       = each.value.collection
  table_stream_arn = module.document-store.stream_arn
  timeout_seconds  = each.value.timeout_seconds
  reader_role_arns = [module.service-task-role[each.value.service_name].arn]
}

module "ecs-job" {
  source   = "../../modules/ecs-job"
  for_each = local.jobs

  region              = var.preferred_region
  feature_environment = local.feature_environment
  cluster_arn         = local.cluster_arn
  service_name        = each.value.service_name
  job_name            = each.value.job_name

  task_role_arn      = module.service-task-role[each.value.service_name].arn
  execution_role_arn = module.task-execution-role.arn

  task_count           = each.value.task_count
  max_retries          = each.value.max_retries
  task_timeout_seconds = each.value.task_timeout_seconds
  cpu                  = each.value.cpu
  memory               = each.value.memory
  schedule             = each.value.schedule
  log_retention_days   = var.log_retention_days

  vpc_id     = local.vpc_id
  subnet_ids = local.private_subnet_ids

  env     = merge(local.env_variables, local.routing_env)
  secrets = local.secret_variables
}
