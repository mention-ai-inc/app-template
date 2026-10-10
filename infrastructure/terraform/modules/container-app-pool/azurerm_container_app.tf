module "container-app-name" {
  source    = "../container-app-name"
  full_name = join("", [var.feature_environment, var.service_name, "-p-", replace(var.pool_name, "_", "-")])
}

locals {
  secret_names = { for name, uri in var.secret_env : name => lower(replace(name, "_", "-")) }

  queue_rules = {
    for rule in var.queue_scale_rules : rule.name => {
      namespace    = var.service_bus_namespace_name
      queueName    = rule.queue_name
      messageCount = tostring(rule.message_count)
    }
  }

  subscription_rules = {
    for rule in var.subscription_scale_rules : rule.name => {
      namespace        = var.service_bus_namespace_name
      topicName        = rule.topic_name
      subscriptionName = rule.subscription_name
      messageCount     = tostring(rule.message_count)
    }
  }

  scale_rules = merge(local.queue_rules, local.subscription_rules)
}

resource "azurerm_container_app" "pool" {
  name                         = module.container-app-name.name
  resource_group_name          = var.resource_group_name
  container_app_environment_id = var.container_app_environment_id
  revision_mode                = "Single"
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

  template {
    min_replicas = var.minimum_instances
    max_replicas = var.maximum_instances

    dynamic "custom_scale_rule" {
      for_each = local.scale_rules

      content {
        name             = custom_scale_rule.key
        custom_rule_type = "azure-servicebus"
        identity_id      = var.identity_id
        metadata         = custom_scale_rule.value
      }
    }

    container {
      name    = "pool"
      image   = var.image
      command = var.command
      cpu     = var.cpu
      memory  = var.memory

      env {
        name  = "COMPONENT_TYPE"
        value = var.component_type
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
      template[0].revision_suffix,
    ]
  }
}
