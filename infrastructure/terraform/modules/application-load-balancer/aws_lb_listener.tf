resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.load-balancer.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate_validation.certificate.certificate_arn

  dynamic "default_action" {
    for_each = var.authenticate_oidc == null ? [] : [var.authenticate_oidc]

    content {
      type  = "authenticate-oidc"
      order = 1

      authenticate_oidc {
        issuer                     = default_action.value.issuer
        authorization_endpoint     = default_action.value.authorization_endpoint
        token_endpoint             = default_action.value.token_endpoint
        user_info_endpoint         = default_action.value.user_info_endpoint
        client_id                  = default_action.value.client_id
        client_secret              = default_action.value.client_secret
        scope                      = default_action.value.scope
        session_timeout            = default_action.value.session_timeout
        on_unauthenticated_request = "authenticate"
      }
    }
  }

  dynamic "default_action" {
    for_each = var.default_target_group_arn == "" ? [] : [var.default_target_group_arn]

    content {
      type             = "forward"
      order            = 2
      target_group_arn = default_action.value
    }
  }

  dynamic "default_action" {
    for_each = var.default_target_group_arn == "" ? [1] : []

    content {
      type  = "fixed-response"
      order = 2

      fixed_response {
        content_type = "application/json"
        message_body = jsonencode({ detail = "Not Found" })
        status_code  = "404"
      }
    }
  }
}

resource "aws_lb_listener" "http-redirect" {
  load_balancer_arn = aws_lb.load-balancer.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}
