module "front-door" {
  source = "../../modules/front-door"

  profile_id          = local.front_door_profile_id
  resource_group_name = local.resource_group_name
  location            = var.preferred_region
  feature_environment = local.feature_environment
  service_name        = "api"
  domain_name         = "${var.api_subdomain}.${var.domain_name}"

  rest_service_origins = {
    for key, server in module.container-app-server :
    local.servers[key].service_name => server.fqdn
  }

  default_identity_id          = module.default-identity.id
  container_app_environment_id = local.container_app_environment_id
  registry_login_server        = local.registry_login_server
  dns_zone_name                = local.dns_zone_name
  dns_zone_resource_group_name = local.dns_zone_resource_group_name
  dns_zone_id                  = local.dns_zone_id
}
