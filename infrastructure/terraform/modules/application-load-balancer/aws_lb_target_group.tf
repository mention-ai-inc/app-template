resource "aws_lb_target_group" "rest" {
  for_each = var.rest_services

  name                 = each.value.target_group_name
  port                 = each.value.container_port
  protocol             = "HTTP"
  target_type          = "ip"
  vpc_id               = var.vpc_id
  deregistration_delay = each.value.deregistration_delay_seconds

  health_check {
    enabled             = true
    path                = each.value.health_check_request_path
    protocol            = "HTTP"
    interval            = each.value.health_check_interval_seconds
    timeout             = each.value.health_check_timeout_seconds
    healthy_threshold   = each.value.health_check_healthy_threshold
    unhealthy_threshold = each.value.health_check_unhealthy_threshold
    matcher             = "200"
  }

  lifecycle {
    create_before_destroy = true
  }
}


resource "aws_lb_target_group" "default" {
  count = var.default_service == null ? 0 : 1

  name                 = var.default_service.target_group_name
  port                 = var.default_service.container_port
  protocol             = "HTTP"
  target_type          = "ip"
  vpc_id               = var.vpc_id
  deregistration_delay = var.default_service.deregistration_delay_seconds

  health_check {
    enabled             = true
    path                = var.default_service.health_check_request_path
    protocol            = "HTTP"
    interval            = var.default_service.health_check_interval_seconds
    timeout             = var.default_service.health_check_timeout_seconds
    healthy_threshold   = var.default_service.health_check_healthy_threshold
    unhealthy_threshold = var.default_service.health_check_unhealthy_threshold
    matcher             = "200"
  }

  lifecycle {
    create_before_destroy = true
  }
}
