module "catchall-server" {
  source = "../container-app-server"

  resource_group_name          = var.resource_group_name
  location                     = var.location
  container_app_environment_id = var.container_app_environment_id
  feature_environment          = var.feature_environment
  service_name                 = "catchall"
  server_name                  = "rest"

  identity_id           = var.default_identity_id
  registry_login_server = var.registry_login_server

  cpu                       = 0.25
  memory                    = "0.5Gi"
  container_concurrency     = 80
  timeout_seconds           = 30
  minimum_instances         = 0
  maximum_instances         = 1
  health_check_request_path = "/"
}
