resource "aws_sns_topic" "alarms" {
  name = "${local.feature_environment}engineering-alarms"
}

resource "aws_sns_topic_subscription" "alarms-email" {
  topic_arn = aws_sns_topic.alarms.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_cloudwatch_metric_alarm" "cache-memory-pressure" {
  count = local.is_production ? 1 : 0

  alarm_name          = "${local.feature_environment}cache-memory-pressure"
  alarm_description   = "Cache memory usage has exceeded 85 percent. Consider a larger redis_node_type."
  namespace           = "AWS/ElastiCache"
  metric_name         = "DatabaseMemoryUsagePercentage"
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 1
  threshold           = 85
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]
  ok_actions          = [aws_sns_topic.alarms.arn]

  dimensions = {
    ReplicationGroupId = module.cache.replication_group_id
  }
}

resource "aws_cloudwatch_metric_alarm" "cache-evictions" {
  count = local.is_production ? 1 : 0

  alarm_name          = "${local.feature_environment}cache-evictions"
  alarm_description   = "The cache has started evicting keys. Data is being lost; raise redis_node_type."
  namespace           = "AWS/ElastiCache"
  metric_name         = "Evictions"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]

  dimensions = {
    ReplicationGroupId = module.cache.replication_group_id
  }
}

locals {
  dead_letter_queue_names = merge(
    { for key, queue in module.sqs-executor-queue : "command-${key}" => queue.dead_letter_queue_name },
    { for key, listener in module.sqs-listener-subscription : "event-${key}" => listener.dead_letter_queue_name },
    { for key, trigger in module.dynamodb-stream-trigger : "trigger-${key}" => trigger.dead_letter_queue_name },
  )
}

resource "aws_cloudwatch_metric_alarm" "dead-letter-queue" {
  for_each = local.dead_letter_queue_names

  alarm_name          = "${each.value}-not-empty"
  alarm_description   = "Messages have exhausted their delivery attempts and are waiting on ${each.value}."
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]

  dimensions = {
    QueueName = each.value
  }
}

resource "aws_cloudwatch_metric_alarm" "api-server-errors" {
  count = local.is_production ? 1 : 0

  alarm_name          = "${local.feature_environment}api-5xx"
  alarm_description   = "The API load balancer is returning server errors."
  namespace           = "AWS/ApplicationELB"
  metric_name         = "HTTPCode_Target_5XX_Count"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 10
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms.arn]

  dimensions = {
    LoadBalancer = replace(module.api-load-balancer.arn, "/^.*:loadbalancer\\//", "")
  }
}

output "alarm_topic_arn" {
  description = "Topic every alarm in this environment publishes to."
  value       = aws_sns_topic.alarms.arn
}
