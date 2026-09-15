terraform {
  backend "azurerm" {
    subscription_id      = "00000000-0000-0000-0000-000000000000"
    tenant_id            = "00000000-0000-0000-0000-000000000000"
    resource_group_name  = "acme-operations-0000"
    storage_account_name = "acmeoperations0000tf"
    container_name       = "terraform-state"
    key                  = "web.tfstate"
    use_azuread_auth     = true
  }

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.40"
    }
    vercel = {
      source  = "vercel/vercel"
      version = "2.8.0"
    }
  }
}

provider "azurerm" {
  features {}

  subscription_id     = var.subscription_id
  tenant_id           = var.tenant_id
  storage_use_azuread = true
}

data "azurerm_key_vault_secret" "vercel-api-token" {
  name         = "VERCEL-TERRAFORM-API-KEY"
  key_vault_id = data.terraform_remote_state.operations.outputs.operations_key_vault_id
}

provider "vercel" {
  api_token = data.azurerm_key_vault_secret.vercel-api-token.value
  team      = var.vercel_team_id
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

module "environment" {
  source = "../../modules/environment"

  feature_resource_group_name    = data.terraform_remote_state.operations.outputs.feature_resource_group_name
  production_resource_group_name = data.terraform_remote_state.operations.outputs.production_resource_group_name
}

locals {
  operations = data.terraform_remote_state.operations.outputs

  feature_environment = module.environment.settings.feature_environment
  resource_group_name = module.environment.settings.resource_group_name
  is_production       = terraform.workspace == "default"

  key_vault_id                 = local.is_production ? local.operations.production_key_vault_id : local.operations.feature_key_vault_id
  dns_zone_name                = local.operations.dns_zone_name
  dns_zone_resource_group_name = local.operations.dns_zone_resource_group_name
}
