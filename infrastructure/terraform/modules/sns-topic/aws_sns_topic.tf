locals {
  name            = join("", [var.feature_environment, replace(var.topic_name, "_", "-")])
  table_name      = replace(join("", [var.feature_environment, var.topic_name]), "-", "_")
  archive_enabled = var.archive_subscriber || var.analytics_subscriber
  archive_prefix  = "${local.name}/"
}

resource "aws_sns_topic" "topic" {
  name = local.name
}
