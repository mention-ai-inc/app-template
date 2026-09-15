module "document-store" {
  source = "../../modules/dynamodb-table"

  table_name    = "${local.feature_environment}acme"
  is_production = local.is_production
}

module "cache" {
  source = "../../modules/elasticache-redis"

  name                = "${local.feature_environment}cache"
  vpc_id              = local.vpc_id
  subnet_ids          = local.private_subnet_ids
  node_type           = local.cache_node_type
  engine_version      = var.redis_engine_version
  is_production       = local.is_production
  auth_token          = data.aws_secretsmanager_secret_version.redis-auth-token.secret_string
  allowed_cidr_blocks = [data.terraform_remote_state.operations.outputs.vpc_cidr_block]
}
