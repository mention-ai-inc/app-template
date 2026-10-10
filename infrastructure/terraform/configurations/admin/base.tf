terraform {
  backend "azurerm" {
    subscription_id      = "00000000-0000-0000-0000-000000000000"
    tenant_id            = "00000000-0000-0000-0000-000000000000"
    resource_group_name  = "acme-operations-0000"
    storage_account_name = "acmeoperations0000tf"
    container_name       = "terraform-state"
    key                  = "admin.tfstate"
    use_azuread_auth     = true
  }

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.40"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 3.5"
    }
    azapi = {
      source  = "azure/azapi"
      version = "~> 2.4"
    }
  }
}

provider "azurerm" {
  features {}

  subscription_id     = var.subscription_id
  tenant_id           = var.tenant_id
  storage_use_azuread = true
}

provider "azuread" {
  tenant_id = var.tenant_id
}

data "terraform_remote_state" "operations" {
  backend   = "azurerm"
  workspace = "default"

  config = {
    subscription_id      = "00000000-0000-0000-0000-000000000000"
    tenant_id            = "00000000-0000-0000-0000-000000000000"
    resource_group_name  = "acme-operations-0000"
    storage_account_name = "acmeoperations0000tf"
    container_name       = "terraform-state"
    key                  = "operations.tfstate"
    use_azuread_auth     = true
  }
}

data "terraform_remote_state" "services" {
  backend   = "azurerm"
  workspace = terraform.workspace

  config = {
    subscription_id      = "00000000-0000-0000-0000-000000000000"
    tenant_id            = "00000000-0000-0000-0000-000000000000"
    resource_group_name  = "acme-operations-0000"
    storage_account_name = "acmeoperations0000tf"
    container_name       = "terraform-state"
    key                  = "services.tfstate"
    use_azuread_auth     = true
  }
}

module "environment" {
  source = "../../modules/environment"

  feature_resource_group_name    = data.terraform_remote_state.operations.outputs.feature_resource_group_name
  production_resource_group_name = data.terraform_remote_state.operations.outputs.production_resource_group_name
}

locals {
  operations = data.terraform_remote_state.operations.outputs
  services   = data.terraform_remote_state.services.outputs

  feature_environment = module.environment.settings.feature_environment
  resource_group_name = module.environment.settings.resource_group_name
  is_production       = terraform.workspace == "default"

  resource_group_id            = local.is_production ? local.operations.production_resource_group_id : local.operations.feature_resource_group_id
  key_vault_uri                = local.is_production ? local.operations.production_key_vault_uri : local.operations.feature_key_vault_uri
  key_vault_id                 = local.is_production ? local.operations.production_key_vault_id : local.operations.feature_key_vault_id
  cosmos_account_name          = local.is_production ? local.operations.production_cosmos_account_name : local.operations.feature_cosmos_account_name
  cosmos_account_id            = local.is_production ? local.operations.production_cosmos_account_id : local.operations.feature_cosmos_account_id
  cosmos_endpoint              = local.is_production ? local.operations.production_cosmos_endpoint : local.operations.feature_cosmos_endpoint
  storage_account_name         = local.is_production ? local.operations.production_storage_account_name : local.operations.feature_storage_account_name
  servicebus_namespace_host    = local.is_production ? local.operations.production_servicebus_namespace_hostname : local.operations.feature_servicebus_namespace_hostname
  container_app_environment_id = local.is_production ? local.operations.production_container_app_environment_id : local.operations.feature_container_app_environment_id
  registry_login_server        = local.operations.container_registry_login_server
  log_analytics_workspace_id   = local.is_production ? local.operations.production_log_analytics_workspace_id : local.operations.feature_log_analytics_workspace_id
  log_analytics_customer_id    = local.is_production ? local.operations.production_log_analytics_customer_id : local.operations.feature_log_analytics_customer_id
  dns_zone_name                = local.operations.dns_zone_name
  dns_zone_resource_group_name = local.operations.dns_zone_resource_group_name
}
