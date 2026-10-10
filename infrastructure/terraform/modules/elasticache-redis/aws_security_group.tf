resource "aws_security_group" "cache" {
  name        = "${var.name}-cache"
  description = "Access to the ${var.name} cache."
  vpc_id      = var.vpc_id
}

resource "aws_vpc_security_group_ingress_rule" "cache" {
  for_each = toset(var.allowed_security_group_ids)

  security_group_id            = aws_security_group.cache.id
  description                  = "Redis from ${each.value}"
  from_port                    = var.port
  to_port                      = var.port
  ip_protocol                  = "tcp"
  referenced_security_group_id = each.value
}

resource "aws_vpc_security_group_ingress_rule" "cache-cidr" {
  for_each = toset(var.allowed_cidr_blocks)

  security_group_id = aws_security_group.cache.id
  description       = "Redis from ${each.value}"
  from_port         = var.port
  to_port           = var.port
  ip_protocol       = "tcp"
  cidr_ipv4         = each.value
}
