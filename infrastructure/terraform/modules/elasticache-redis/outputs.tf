output "primary_endpoint" {
  description = "Hostname clients write to."
  value       = aws_elasticache_replication_group.cache.primary_endpoint_address
}

output "reader_endpoint" {
  description = "Hostname clients read from when the group has replicas."
  value       = aws_elasticache_replication_group.cache.reader_endpoint_address
}

output "port" {
  description = "Port the cache listens on."
  value       = var.port
}

output "replication_group_id" {
  description = "Identifier of the replication group, used by CloudWatch alarms."
  value       = aws_elasticache_replication_group.cache.replication_group_id
}

output "security_group_id" {
  description = "Security group guarding the cache."
  value       = aws_security_group.cache.id
}
