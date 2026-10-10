locals {
  service_clauses = {
    for index, subscription in local.indexed_subscriptions :
    index => join(" OR ", [for name in split("|", subscription.source_service_name) : "service = '${name}'"])
  }

  event_clauses = {
    for index, subscription in local.indexed_subscriptions :
    index => join(" OR ", [for name in split("|", subscription.event_name) : "event = '${name}'"])
  }

  model_clauses = {
    for index, subscription in local.indexed_subscriptions :
    index => subscription.model_name != null && subscription.model_name != "" ? " AND (${join(" OR ", [for name in split("|", subscription.model_name) : "model_name = '${name}'"])})" : ""
  }
}

resource "azurerm_servicebus_subscription_rule" "listener" {
  for_each = local.indexed_subscriptions

  name            = "match"
  subscription_id = azurerm_servicebus_subscription.listener[each.key].id
  filter_type     = "SqlFilter"
  sql_filter      = "(${local.service_clauses[each.key]}) AND (${local.event_clauses[each.key]})${local.model_clauses[each.key]}"
}
