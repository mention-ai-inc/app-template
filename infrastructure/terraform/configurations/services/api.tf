module "load-balancer" {
  source = "../../modules/load-balancer"

  project_id          = local.project
  region              = var.preferred_region
  feature_environment = local.feature_environment
  service_name        = "api"
  domain_name         = "${var.api_subdomain}.${var.domain_name}"
  rest_service_links = {
    for service in module.cloud-run-service-server
    : service.service_name => service.backend_service_self_link
  }
  dns_managed_zone               = var.dns_managed_zone
  default_service_account_email  = module.default-service-account.email
  default_service_vpc_network    = data.terraform_remote_state.operations.outputs.shared-vpc-network-id
  default_service_vpc_subnetwork = data.terraform_remote_state.operations.outputs.cloud-run-subnetwork-id
}
