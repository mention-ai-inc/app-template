module "catchall-server" {
  source = "../../modules/cloud-run-server"

  project_id            = var.project_id
  region                = var.region
  feature_environment   = var.feature_environment
  service_name          = "catchall"
  server_name           = "rest"
  service_account_email = var.default_service_account_email

  backend_service_name_suffix = "-v2"

  cpu                   = "1"
  memory                = "512Mi"
  container_concurrency = 80
  timeout_seconds       = 30
  minimum_instances     = 0
  maximum_instances     = 1
  vpc_network           = var.default_service_vpc_network
  vpc_subnetwork        = var.default_service_vpc_subnetwork
}
