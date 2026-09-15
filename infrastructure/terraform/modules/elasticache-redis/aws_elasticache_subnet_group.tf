resource "aws_elasticache_subnet_group" "cache" {
  name       = var.name
  subnet_ids = var.subnet_ids
}
