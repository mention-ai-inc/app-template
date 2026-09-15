resource "aws_ecs_service" "pool" {
  name                   = module.resource-name.name
  cluster                = var.cluster_arn
  task_definition        = aws_ecs_task_definition.pool.arn
  desired_count          = max(var.minimum_instances, 1)
  launch_type            = "FARGATE"
  propagate_tags         = "SERVICE"
  enable_execute_command = true

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = [aws_security_group.pool.id]
    assign_public_ip = false
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  lifecycle {
    ignore_changes = [task_definition, desired_count]
  }
}
