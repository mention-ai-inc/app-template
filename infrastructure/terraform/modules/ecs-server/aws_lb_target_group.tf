resource "aws_lb_target_group" "server" {
  name                 = module.resource-name.name
  port                 = var.container_port
  protocol             = "HTTP"
  target_type          = "ip"
  vpc_id               = var.vpc_id
  deregistration_delay = var.deregistration_delay_seconds

  health_check {
    enabled             = true
    path                = coalesce(var.health_check_request_path, "/${var.server_name}/${var.service_name}/health")
    protocol            = "HTTP"
    interval            = var.health_check_interval_seconds
    timeout             = var.health_check_timeout_seconds
    healthy_threshold   = var.health_check_healthy_threshold
    unhealthy_threshold = var.health_check_unhealthy_threshold
    matcher             = "200"
  }

  lifecycle {
    create_before_destroy = true
  }
}
