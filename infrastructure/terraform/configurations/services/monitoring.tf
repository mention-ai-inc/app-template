resource "azurerm_monitor_action_group" "engineering" {
  name                = "${local.feature_environment}engineering-alerts"
  resource_group_name = local.resource_group_name
  short_name          = "eng"

  email_receiver {
    name          = "engineering"
    email_address = "engineer@acme.example.com"
  }
}

resource "azurerm_monitor_metric_alert" "redis-memory-pressure" {
  count = local.is_production ? 1 : 0

  name                = "${local.feature_environment}redis-memory-pressure"
  resource_group_name = local.resource_group_name
  scopes              = [module.redis.id]
  description         = "Redis memory usage has exceeded 85% of the configured maximum. Consider a larger sku_name or capacity."
  frequency           = "PT1M"
  window_size         = "PT5M"
  severity            = 2

  criteria {
    metric_namespace = "Microsoft.Cache/redis"
    metric_name      = "usedmemorypercentage"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 85
  }

  action {
    action_group_id = azurerm_monitor_action_group.engineering.id
  }
}

resource "azurerm_monitor_metric_alert" "redis-evictions" {
  count = local.is_production ? 1 : 0

  name                = "${local.feature_environment}redis-evictions"
  resource_group_name = local.resource_group_name
  scopes              = [module.redis.id]
  description         = "Redis has started evicting keys due to memory pressure. Data is being lost. Raise sku_name or capacity immediately."
  frequency           = "PT1M"
  window_size         = "PT5M"
  severity            = 1

  criteria {
    metric_namespace = "Microsoft.Cache/redis"
    metric_name      = "evictedkeys"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 0
  }

  action {
    action_group_id = azurerm_monitor_action_group.engineering.id
  }
}
