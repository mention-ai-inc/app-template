locals {
  backlog_metric_ids = [for index in range(length(var.backlog_queue_names)) : "q${index}"]
}

resource "aws_appautoscaling_policy" "backlog" {
  count = length(var.backlog_queue_names) > 0 ? 1 : 0

  name               = "${module.resource-name.name}-backlog"
  policy_type        = "TargetTrackingScaling"
  service_namespace  = aws_appautoscaling_target.pool.service_namespace
  scalable_dimension = aws_appautoscaling_target.pool.scalable_dimension
  resource_id        = aws_appautoscaling_target.pool.resource_id

  target_tracking_scaling_policy_configuration {
    target_value       = var.target_messages_per_task
    scale_in_cooldown  = var.scale_in_cooldown_seconds
    scale_out_cooldown = var.scale_out_cooldown_seconds

    customized_metric_specification {
      metrics {
        id          = "backlog"
        expression  = "(${join(" + ", local.backlog_metric_ids)}) / IF(tasks > 0, tasks, 1)"
        label       = "Waiting messages per running task"
        return_data = true
      }

      dynamic "metrics" {
        for_each = { for index, queue_name in var.backlog_queue_names : "q${index}" => queue_name }

        content {
          id          = metrics.key
          return_data = false

          metric_stat {
            stat = "Average"

            metric {
              namespace   = "AWS/SQS"
              metric_name = "ApproximateNumberOfMessagesVisible"

              dimensions {
                name  = "QueueName"
                value = metrics.value
              }
            }
          }
        }
      }

      metrics {
        id          = "tasks"
        return_data = false

        metric_stat {
          stat = "Average"

          metric {
            namespace   = "ECS/ContainerInsights"
            metric_name = "RunningTaskCount"

            dimensions {
              name  = "ClusterName"
              value = var.cluster_name
            }

            dimensions {
              name  = "ServiceName"
              value = aws_ecs_service.pool.name
            }
          }
        }
      }
    }
  }
}

resource "aws_appautoscaling_policy" "cpu" {
  count = length(var.backlog_queue_names) > 0 ? 0 : 1

  name               = "${module.resource-name.name}-cpu"
  policy_type        = "TargetTrackingScaling"
  service_namespace  = aws_appautoscaling_target.pool.service_namespace
  scalable_dimension = aws_appautoscaling_target.pool.scalable_dimension
  resource_id        = aws_appautoscaling_target.pool.resource_id

  target_tracking_scaling_policy_configuration {
    target_value       = 60
    scale_in_cooldown  = var.scale_in_cooldown_seconds
    scale_out_cooldown = var.scale_out_cooldown_seconds

    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
  }
}
