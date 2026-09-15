resource "aws_ecs_service" "server" {
  name                              = module.resource-name.name
  cluster                           = var.cluster_arn
  task_definition                   = aws_ecs_task_definition.server.arn
  desired_count                     = max(var.minimum_instances, 1)
  launch_type                       = "FARGATE"
  health_check_grace_period_seconds = 60
  propagate_tags                    = "SERVICE"
  enable_execute_command            = true

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = [aws_security_group.server.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.server.arn
    container_name   = "app"
    container_port   = var.container_port
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  lifecycle {
    ignore_changes = [task_definition, desired_count]
  }
}
