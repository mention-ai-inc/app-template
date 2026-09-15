resource "azurerm_cosmosdb_sql_database" "services" {
  name                = "${local.feature_environment}acme"
  resource_group_name = local.resource_group_name
  account_name        = local.cosmos_account_name

  dynamic "autoscale_settings" {
    for_each = local.is_production ? [1] : []

    content {
      max_throughput = var.cosmos_max_throughput
    }
  }
}

resource "azurerm_cosmosdb_sql_container" "service" {
  for_each = toset(keys(var.services))

  name                  = each.value
  resource_group_name   = local.resource_group_name
  account_name          = local.cosmos_account_name
  database_name         = azurerm_cosmosdb_sql_database.services.name
  partition_key_paths   = ["/partitionKey"]
  partition_key_version = 2
  default_ttl           = -1

  indexing_policy {
    indexing_mode = "consistent"

    included_path {
      path = "/*"
    }

    excluded_path {
      path = "/\"_etag\"/?"
    }

    composite_index {
      index {
        path  = "/documentType"
        order = "ascending"
      }
      index {
        path  = "/createdAt"
        order = "ascending"
      }
    }

    composite_index {
      index {
        path  = "/documentType"
        order = "ascending"
      }
      index {
        path  = "/dispatched"
        order = "ascending"
      }
    }
  }
}

module "redis" {
  source = "../../modules/redis-cache"

  name                = "${local.feature_environment}acme-cache"
  resource_group_name = local.resource_group_name
  location            = var.preferred_region

  sku_name = local.redis_sku_name
  family   = local.redis_family
  capacity = local.redis_capacity
}

resource "azurerm_key_vault_secret" "redis-password" {
  name         = join("-", compact([local.feature_environment, "REDIS-PASSWORD"]))
  key_vault_id = local.key_vault_id
  value        = module.redis.primary_access_key
  content_type = "text/plain"
}
