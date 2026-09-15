resource "aws_cloudwatch_log_group" "job" {
  name              = "/ecs/${module.resource-name.name}"
  retention_in_days = var.log_retention_days
}
