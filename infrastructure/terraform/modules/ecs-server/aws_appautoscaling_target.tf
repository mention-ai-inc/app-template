resource "aws_appautoscaling_target" "server" {
  service_namespace  = "ecs"
  scalable_dimension = "ecs:service:DesiredCount"
  resource_id        = "service/${var.cluster_name}/${aws_ecs_service.server.name}"
  min_capacity       = max(var.minimum_instances, 1)
  max_capacity       = max(var.maximum_instances, max(var.minimum_instances, 1))
}
