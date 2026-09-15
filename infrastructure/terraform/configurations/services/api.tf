module "api-load-balancer" {
  source = "../../modules/application-load-balancer"

  feature_environment = local.feature_environment
  surface_name        = "api"
  domain_name         = "${var.api_subdomain}.${var.domain_name}"
  hosted_zone_id      = local.hosted_zone_id

  vpc_id     = local.vpc_id
  subnet_ids = local.public_subnet_ids

  rest_service_target_groups = {
    for key, server in module.ecs-server : local.servers[key].service_name => server.target_group_arn
  }

  deletion_protection_enabled = local.is_production
  access_log_bucket           = data.terraform_remote_state.operations.outputs.load_balancer_logs_bucket_name
}

output "api_fqdn" {
  description = "Hostname the API is served on."
  value       = module.api-load-balancer.fqdn
}
