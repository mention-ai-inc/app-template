resource "aws_elasticache_parameter_group" "cache" {
  name   = var.name
  family = "redis7"

  parameter {
    name  = "maxmemory-policy"
    value = var.maximum_memory_policy
  }
}
