subscription_id                = "00000000-0000-0000-0000-000000000000"
tenant_id                      = "00000000-0000-0000-0000-000000000000"
operations_resource_group_name = "acme-operations-0000"
production_resource_group_name = "acme-production-0000"
feature_resource_group_name    = "acme-feature-0000"
preferred_region               = "eastus"
github_repo                    = "mention-ai-inc/app-template"
domain_name                    = "acme.example.com"

container_registry_name = "acmeoperations0000"

operations_key_vault_name = "acme-operations-0000-kv"
production_key_vault_name = "acme-production-0000-kv"
feature_key_vault_name    = "acme-feature-0000-kv"

operations_storage_account_name = "acmeoperations0000"
production_storage_account_name = "acmeproduction0000"
feature_storage_account_name    = "acmefeature0000"
blob_cors_origins               = ["https://app.acme.example.com"]

production_servicebus_namespace_name = "acme-production-0000"
feature_servicebus_namespace_name    = "acme-feature-0000"

production_cosmos_account_name           = "acme-production-0000"
feature_cosmos_account_name              = "acme-feature-0000"
production_cosmos_backup_retention_hours = 720

production_container_app_environment_name = "acme-production-0000"
feature_container_app_environment_name    = "acme-feature-0000"

production_log_retention_days = 90
feature_log_retention_days    = 30

production_front_door_profile_name  = "acme-production-0000"
feature_front_door_profile_name     = "acme-feature-0000"
front_door_sku_name                 = "Standard_AzureFrontDoor"
front_door_response_timeout_seconds = 120
