module "container-app-name" {
  source    = "../container-app-name"
  full_name = join("", [var.feature_environment, var.service_name, "-j-", replace(var.job_name, "_", "-")])
}

locals {
  secret_names = { for name, uri in var.secret_env : name => lower(replace(name, "_", "-")) }
}

resource "azurerm_container_app_job" "job" {
  name                         = module.container-app-name.name
  resource_group_name          = var.resource_group_name
  location                     = var.location
  container_app_environment_id = var.container_app_environment_id
  replica_timeout_in_seconds   = var.task_timeout_seconds
  replica_retry_limit          = var.max_retries
  tags                         = var.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [var.identity_id]
  }

  registry {
    server   = var.registry_login_server
    identity = var.identity_id
  }

  dynamic "secret" {
    for_each = var.secret_env

    content {
      name                = local.secret_names[secret.key]
      key_vault_secret_id = secret.value
      identity            = var.identity_id
    }
  }

  dynamic "schedule_trigger_config" {
    for_each = var.schedule != "" ? [1] : []

    content {
      cron_expression          = var.schedule
      parallelism              = var.parallelism
      replica_completion_count = var.task_count
    }
  }

  dynamic "manual_trigger_config" {
    for_each = var.schedule == "" ? [1] : []

    content {
      parallelism              = var.parallelism
      replica_completion_count = var.task_count
    }
  }

  template {
    container {
      name    = "job"
      image   = var.image
      command = var.command
      cpu     = var.cpu
      memory  = var.memory

      env {
        name  = "COMPONENT_TYPE"
        value = "job"
      }

      env {
        name  = "COMPONENT_NAME"
        value = var.job_name
      }

      dynamic "env" {
        for_each = var.env

        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = var.secret_env

        content {
          name        = env.key
          secret_name = local.secret_names[env.key]
        }
      }
    }
  }

  lifecycle {
    ignore_changes = [
      template[0].container[0].image,
      template[0].container[0].command,
    ]
  }
}
