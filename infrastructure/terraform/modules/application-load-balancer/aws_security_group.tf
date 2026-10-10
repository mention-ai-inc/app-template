locals {
  name = "${var.feature_environment}${var.surface_name}"
  fqdn = "${var.feature_environment}${var.domain_name}"
}

resource "aws_security_group" "load-balancer" {
  name        = "${local.name}-lb"
  description = "Public entry point for the ${var.surface_name} surface."
  vpc_id      = var.vpc_id
}

resource "aws_vpc_security_group_ingress_rule" "https" {
  for_each = toset(var.ingress_cidr_blocks)

  security_group_id = aws_security_group.load-balancer.id
  description       = "HTTPS from ${each.value}"
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
  cidr_ipv4         = each.value
}

resource "aws_vpc_security_group_ingress_rule" "http" {
  for_each = toset(var.ingress_cidr_blocks)

  security_group_id = aws_security_group.load-balancer.id
  description       = "HTTP from ${each.value}, redirected to HTTPS"
  from_port         = 80
  to_port           = 80
  ip_protocol       = "tcp"
  cidr_ipv4         = each.value
}

resource "aws_vpc_security_group_egress_rule" "targets" {
  security_group_id = aws_security_group.load-balancer.id
  description       = "Forwarded requests to the targets"
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}
