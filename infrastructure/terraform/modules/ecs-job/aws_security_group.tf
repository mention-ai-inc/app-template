resource "aws_security_group" "job" {
  name        = "${module.resource-name.name}-tasks"
  description = "Tasks of the ${var.service_name} ${var.job_name} job."
  vpc_id      = var.vpc_id
}

resource "aws_vpc_security_group_egress_rule" "all" {
  security_group_id = aws_security_group.job.id
  description       = "Outbound traffic to AWS APIs, the cache, and third parties"
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}
