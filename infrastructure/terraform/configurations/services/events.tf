module "service-bus-topics" {
  for_each = var.topics
  source   = "../../modules/service-bus-topic"

  namespace_id        = local.servicebus_namespace_id
  feature_environment = local.feature_environment
  topic_name          = each.value.name
  archive             = tobool(lookup(each.value, "archive", false))
}
