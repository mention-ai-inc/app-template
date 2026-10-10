resource "aws_elasticache_replication_group" "cache" {
  replication_group_id       = var.name
  description                = "Cache for ${var.name}."
  engine                     = "redis"
  engine_version             = var.engine_version
  node_type                  = var.node_type
  port                       = var.port
  parameter_group_name       = aws_elasticache_parameter_group.cache.name
  subnet_group_name          = aws_elasticache_subnet_group.cache.name
  security_group_ids         = [aws_security_group.cache.id]
  num_cache_clusters         = var.is_production ? 2 : 1
  automatic_failover_enabled = var.is_production
  multi_az_enabled           = var.is_production
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                 = var.auth_token
  snapshot_retention_limit   = var.is_production ? 7 : 0
  apply_immediately          = !var.is_production
}
