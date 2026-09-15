resource "aws_security_group" "server" {
  name        = "${module.resource-name.name}-tasks"
  description = "Tasks of the ${var.service_name} ${var.server_name} server."
  vpc_id      = var.vpc_id
}

resource "aws_vpc_security_group_ingress_rule" "from-load-balancer" {
  security_group_id            = aws_security_group.server.id
  description                  = "Requests from the load balancer"
  from_port                    = var.container_port
  to_port                      = var.container_port
  ip_protocol                  = "tcp"
  referenced_security_group_id = var.load_balancer_security_group_id
}

resource "aws_vpc_security_group_egress_rule" "all" {
  security_group_id = aws_security_group.server.id
  description       = "Outbound traffic to AWS APIs, the cache, and third parties"
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}
