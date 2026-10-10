locals {
  mcp_fqdn            = "${local.feature_environment}${var.mcp_subdomain}.${var.domain_name}"
  mcp_dns_record_name = "${local.feature_environment}${var.mcp_subdomain}"
  api_url             = "https://${local.feature_environment}${var.api_subdomain}.${var.domain_name}"
}

module "mcp-identity" {
  source = "../../modules/managed-identity"

  name                = "${local.feature_environment}mcpclient-s"
  resource_group_name = local.resource_group_name
  location            = var.preferred_region

  role_assignments = [
    {
      role  = "Key Vault Secrets User"
      scope = local.resource_group_id
    },
    {
      role  = "Monitoring Metrics Publisher"
      scope = local.resource_group_id
    },
    {
      role  = "AcrPull"
      scope = local.operations.operations_resource_group_id
    },
  ]
}

module "mcp-server" {
  source = "../../modules/container-app-server"

  resource_group_name          = local.resource_group_name
  location                     = var.preferred_region
  container_app_environment_id = local.container_app_environment_id
  feature_environment          = local.feature_environment
  service_name                 = "mcp"
  server_name                  = "rest"

  identity_id           = module.mcp-identity.id
  registry_login_server = local.registry_login_server
  image                 = "${local.registry_login_server}/${local.feature_environment}mcp:main"

  cpu                       = 0.5
  memory                    = "1Gi"
  container_concurrency     = 80
  timeout_seconds           = 300
  minimum_instances         = 0
  maximum_instances         = 10
  health_check_request_path = "/health"

  custom_domain_fqdn           = local.mcp_fqdn
  dns_record_name              = local.mcp_dns_record_name
  dns_zone_name                = local.dns_zone_name
  dns_zone_resource_group_name = local.dns_zone_resource_group_name

  secret_env = {
    "CLERK_SECRET_KEY" = "${local.key_vault_uri}secrets/CLERK-SECRET-KEY"
  }

  env = {
    "AZURE_CLIENT_ID"       = module.mcp-identity.client_id
    "API_URL"               = local.api_url
    "CLERK_PUBLISHABLE_KEY" = module.environment.settings.tokens.clerk_publishable_key
  }
}

output "mcp_url" {
  description = "The URL the MCP server is served at."
  value       = module.mcp-server.url
}
