module "rest-target-group-name" {
  source   = "../../modules/resource-name"
  for_each = local.servers

  full_name  = join("", [local.feature_environment, replace(each.value.service_name, "_", "-"), "-s-", replace(each.value.server_name, "_", "-")])
  max_length = 32
}

module "api-load-balancer" {
  source = "../../modules/application-load-balancer"

  feature_environment = local.feature_environment
  surface_name        = "api"
  domain_name         = "${var.api_subdomain}.${var.domain_name}"
  hosted_zone_id      = local.hosted_zone_id

  vpc_id     = local.vpc_id
  subnet_ids = local.public_subnet_ids

  rest_services = {
    for key, server in local.servers : server.service_name => {
      target_group_name                = module.rest-target-group-name[key].name
      container_port                   = 8080
      health_check_request_path        = "/rest/${server.service_name}/health"
      deregistration_delay_seconds     = 30
      health_check_interval_seconds    = 30
      health_check_timeout_seconds     = 5
      health_check_healthy_threshold   = 2
      health_check_unhealthy_threshold = 3
    }
  }

  deletion_protection_enabled = local.is_production
  access_log_bucket           = data.terraform_remote_state.operations.outputs.load_balancer_logs_bucket_name
}

output "api_fqdn" {
  description = "Hostname the API is served on."
  value       = module.api-load-balancer.fqdn
}
