resource "aws_lb" "load-balancer" {
  name                       = "${local.name}-lb"
  load_balancer_type         = "application"
  internal                   = false
  subnets                    = var.subnet_ids
  security_groups            = [aws_security_group.load-balancer.id]
  idle_timeout               = var.idle_timeout_seconds
  enable_deletion_protection = var.deletion_protection_enabled
  drop_invalid_header_fields = true

  dynamic "access_logs" {
    for_each = var.access_log_bucket == "" ? [] : [var.access_log_bucket]

    content {
      enabled = true
      bucket  = access_logs.value
      prefix  = local.name
    }
  }
}
