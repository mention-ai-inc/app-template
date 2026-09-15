locals {
  admin_fqdn            = "${local.feature_environment}${var.admin_subdomain}.${var.domain_name}"
  admin_dns_record_name = "${local.feature_environment}${var.admin_subdomain}"

  env_variables = {
    "AZURE_SUBSCRIPTION_ID" = var.subscription_id
    "AZURE_RESOURCE_GROUP"  = local.resource_group_name
    "AZURE_CLIENT_ID"       = module.admin-identity.client_id
    "FEATURE_ENVIRONMENT"   = local.feature_environment
    "PYTHONWARNINGS"        = var.python_warnings
    "AZURE_KEY_VAULT_URI"   = local.key_vault_uri
    "AZURE_REGION"          = var.preferred_region
    "COSMOS_ENDPOINT"       = local.cosmos_endpoint
    "COSMOS_DATABASE"       = local.services.cosmos_database_name
    "SERVICE_BUS_NAMESPACE" = local.servicebus_namespace_host
    "BLOB_ACCOUNT_URL"      = "https://${local.storage_account_name}.blob.core.windows.net"
    "REDIS_HOST"            = local.services.redis_hostname
    "REDIS_PORT"            = tostring(local.services.redis_ssl_port)
    "REDIS_SSL"             = "true"
  }

  admin_image = "${local.registry_login_server}/${local.feature_environment}admin:main"
}

resource "azurerm_cosmosdb_sql_container" "admin" {
  name                  = "admin"
  resource_group_name   = local.resource_group_name
  account_name          = local.cosmos_account_name
  database_name         = local.services.cosmos_database_name
  partition_key_paths   = ["/partitionKey"]
  partition_key_version = 2
  default_ttl           = -1

  indexing_policy {
    indexing_mode = "consistent"

    included_path {
      path = "/*"
    }

    excluded_path {
      path = "/\"_etag\"/?"
    }

    composite_index {
      index {
        path  = "/documentType"
        order = "ascending"
      }
      index {
        path  = "/createdAt"
        order = "ascending"
      }
    }
  }
}

module "admin-backfill-job" {
  source = "../../modules/container-app-job"

  resource_group_name          = local.resource_group_name
  location                     = var.preferred_region
  container_app_environment_id = local.container_app_environment_id
  feature_environment          = local.feature_environment
  service_name                 = "admin"
  job_name                     = "backfill"

  identity_id           = module.admin-identity.id
  registry_login_server = local.registry_login_server
  image                 = local.admin_image
  command               = ["admin", "backfill"]

  max_retries          = 0
  task_timeout_seconds = 3600
  cpu                  = 1
  memory               = "2Gi"

  secret_env = local.secret_env
  env        = local.env_variables
}

module "admin-seed-job" {
  count  = local.is_production ? 0 : 1
  source = "../../modules/container-app-job"

  resource_group_name          = local.resource_group_name
  location                     = var.preferred_region
  container_app_environment_id = local.container_app_environment_id
  feature_environment          = local.feature_environment
  service_name                 = "admin"
  job_name                     = "seed"

  identity_id           = module.admin-identity.id
  registry_login_server = local.registry_login_server
  image                 = local.admin_image
  command               = ["admin", "seed"]

  max_retries          = 0
  task_timeout_seconds = 21600
  cpu                  = 1
  memory               = "2Gi"

  secret_env = local.secret_env
  env        = local.env_variables
}

module "admin-server" {
  source = "../../modules/container-app-server"

  resource_group_name          = local.resource_group_name
  location                     = var.preferred_region
  container_app_environment_id = local.container_app_environment_id
  feature_environment          = local.feature_environment
  service_name                 = "admin"
  server_name                  = "rest"

  identity_id           = module.admin-identity.id
  registry_login_server = local.registry_login_server
  image                 = local.admin_image

  cpu                       = 0.5
  memory                    = "1Gi"
  container_concurrency     = 80
  timeout_seconds           = 300
  minimum_instances         = 0
  maximum_instances         = 3
  health_check_request_path = "/health"
  ip_allowlist              = var.admin_ip_allowlist

  custom_domain_fqdn           = local.admin_fqdn
  dns_record_name              = local.admin_dns_record_name
  dns_zone_name                = local.dns_zone_name
  dns_zone_resource_group_name = local.dns_zone_resource_group_name

  secret_env = local.secret_env
  env = merge(local.env_variables, {
    "SERVICE"               = "admin"
    "ADMIN_ENTRA_TENANT_ID" = var.tenant_id
    "ADMIN_ENTRA_CLIENT_ID" = azuread_application.admin.client_id
    "STAFF_ALLOWLIST"       = join(",", local.staff_allowlist)
  })
}

module "admin-trigger-pool" {
  source = "../../modules/container-app-pool"

  resource_group_name          = local.resource_group_name
  container_app_environment_id = local.container_app_environment_id
  feature_environment          = local.feature_environment
  service_name                 = "admin"
  pool_name                    = "triggers"
  component_type               = "trigger"

  identity_id           = module.admin-identity.id
  registry_login_server = local.registry_login_server
  image                 = local.admin_image

  minimum_instances = 1
  maximum_instances = 1

  secret_env = local.secret_env
  env = merge(local.env_variables, {
    "SERVICE"                   = "admin"
    "CHANGE_FEED_TRIGGERS_JSON" = jsonencode({ "admin:publish_audit_event" = module.admin-audit-trigger.routing })
  })
}

module "admin-audit-trigger" {
  source = "../../modules/cosmos-change-feed-trigger"

  resource_group_name    = local.resource_group_name
  cosmos_account_name    = local.cosmos_account_name
  cosmos_database_name   = local.services.cosmos_database_name
  watched_container_name = azurerm_cosmosdb_sql_container.admin.name
  service_name           = "admin"
  trigger_name           = "publish_audit_event"
  document_type          = "audit"

  provisioned_throughput = local.is_production
}

output "admin_url" {
  description = "The URL the admin API is served at."
  value       = module.admin-server.url
}
