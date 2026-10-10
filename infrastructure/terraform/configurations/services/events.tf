module "sns-topics" {
  source   = "../../modules/sns-topic"
  for_each = var.topics

  feature_environment = local.feature_environment
  topic_name          = each.value.name

  archive_subscriber   = tobool(lookup(each.value, "archive_subscriber", false))
  analytics_subscriber = tobool(lookup(each.value, "analytics_subscriber", false))
  archive_bucket_arn   = each.key == "audit_events" ? aws_s3_bucket.audit-archive.arn : module.event-archive.bucket_arn
  glue_database_name   = each.key == "audit_events" ? aws_glue_catalog_database.audit-export.name : aws_glue_catalog_database.event-export.name

  publisher_role_arns = [for role in module.service-task-role : role.arn]
}

locals {
  topic_arns = { for key, topic in module.sns-topics : var.topics[key].name => topic.topic_arn }
}

output "topic_arns" {
  description = "ARNs of the event topics, keyed by topic name."
  value       = local.topic_arns
}
