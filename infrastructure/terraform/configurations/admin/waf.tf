resource "aws_wafv2_web_acl" "admin" {
  name        = "${local.feature_environment}admin"
  description = "Rate limiting for the admin API. The load balancer's OIDC authentication is the gate; this guards against brute force and abuse."
  scope       = "REGIONAL"

  default_action {
    allow {}
  }

  rule {
    name     = "rate-limit-per-address"
    priority = 1

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit                 = var.rate_limit_per_five_minutes
        aggregate_key_type    = "IP"
        evaluation_window_sec = 300
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.feature_environment}admin-rate-limit"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${local.feature_environment}admin"
    sampled_requests_enabled   = true
  }
}
