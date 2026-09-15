resource "aws_lb_listener_rule" "rest" {
  for_each = var.rest_service_target_groups

  listener_arn = aws_lb_listener.https.arn
  priority     = index(sort(keys(var.rest_service_target_groups)), each.key) + 100

  dynamic "action" {
    for_each = var.authenticate_oidc == null ? [] : [var.authenticate_oidc]

    content {
      type  = "authenticate-oidc"
      order = 1

      authenticate_oidc {
        issuer                     = action.value.issuer
        authorization_endpoint     = action.value.authorization_endpoint
        token_endpoint             = action.value.token_endpoint
        user_info_endpoint         = action.value.user_info_endpoint
        client_id                  = action.value.client_id
        client_secret              = action.value.client_secret
        scope                      = action.value.scope
        session_timeout            = action.value.session_timeout
        on_unauthenticated_request = "authenticate"
      }
    }
  }

  action {
    type             = "forward"
    order            = 2
    target_group_arn = each.value
  }

  condition {
    host_header {
      values = [local.fqdn]
    }
  }

  condition {
    path_pattern {
      values = ["/rest/${each.key}/*"]
    }
  }
}
