output "subscriptions" {
  description = "The topic and subscription names the listener pool drains, one entry per configured subscription."
  value = [
    for index, subscription in local.indexed_subscriptions : {
      topic_name        = "${var.feature_environment}${subscription.topic_name}"
      subscription_name = azurerm_servicebus_subscription.listener[index].name
    }
  ]
}
