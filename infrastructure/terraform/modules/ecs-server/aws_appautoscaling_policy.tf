resource "aws_appautoscaling_policy" "cpu" {
  name               = "${module.resource-name.name}-cpu"
  policy_type        = "TargetTrackingScaling"
  service_namespace  = aws_appautoscaling_target.server.service_namespace
  scalable_dimension = aws_appautoscaling_target.server.scalable_dimension
  resource_id        = aws_appautoscaling_target.server.resource_id

  target_tracking_scaling_policy_configuration {
    target_value       = var.target_cpu_utilization
    scale_in_cooldown  = var.scale_in_cooldown_seconds
    scale_out_cooldown = var.scale_out_cooldown_seconds

    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
  }
}
