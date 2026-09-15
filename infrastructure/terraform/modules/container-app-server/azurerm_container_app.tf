module "container-app-name" {
  source    = "../container-app-name"
  full_name = join("", [var.feature_environment, var.service_name, "-s-", replace(var.server_name, "_", "-")])
}

locals {
  secret_names      = { for name, uri in var.secret_env : name => lower(replace(name, "_", "-")) }
  probe_path        = coalesce(var.health_check_request_path, "/${var.server_name}/${var.service_name}/health")
  has_custom_domain = var.custom_domain_fqdn != ""
}

resource "azurerm_container_app" "server" {
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

  ingress {
    external_enabled = var.external_enabled
    target_port      = var.target_port
    transport        = "auto"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }

    dynamic "ip_security_restriction" {
      for_each = var.ip_allowlist

      content {
        name             = ip_security_restriction.value.name
        ip_address_range = ip_security_restriction.value.ip_address_range
        action           = "Allow"
      }
    }
  }

  template {
    min_replicas = var.minimum_instances
    max_replicas = var.maximum_instances

    http_scale_rule {
      name                = "http"
      concurrent_requests = tostring(var.container_concurrency)
    }

    container {
      name    = "server"
      image   = var.image
      command = var.command
      cpu     = var.cpu
      memory  = var.memory

      env {
        name  = "COMPONENT_TYPE"
        value = "server"
      }

      env {
        name  = "COMPONENT_NAME"
        value = var.server_name
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

      readiness_probe {
        transport = "HTTP"
        port      = var.target_port
        path      = local.probe_path
      }

      liveness_probe {
        transport     = "HTTP"
        port          = var.target_port
        path          = local.probe_path
        initial_delay = 10
        timeout       = 5
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
