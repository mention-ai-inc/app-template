resource "aws_wafv2_web_acl_association" "load-balancer" {
  count = var.web_acl_arn == "" ? 0 : 1

  resource_arn = aws_lb.load-balancer.arn
  web_acl_arn  = var.web_acl_arn
}
