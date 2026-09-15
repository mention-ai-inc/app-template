locals {
  terraform_role_arn = "arn:aws:iam::000000000000:role/terraform"
}

provider "aws" {
  region = var.preferred_region

  assume_role {
    role_arn     = local.terraform_role_arn
    session_name = "terraform-mcp"
  }

  default_tags {
    tags = {
      Repository    = var.github_repo
      Configuration = "mcp"
      Environment   = terraform.workspace
      ManagedBy     = "terraform"
    }
  }
}

terraform {
  backend "s3" {
    bucket               = "acme-operations-0000--terraform-state"
    key                  = "mcp/terraform.tfstate"
    workspace_key_prefix = "workspaces"
    region               = "us-east-1"
    use_lockfile         = true
    encrypt              = true

    assume_role = {
      role_arn = "arn:aws:iam::000000000000:role/terraform"
    }
  }

  required_version = ">= 1.10.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

data "terraform_remote_state" "operations" {
  backend   = "s3"
  workspace = "default"

  config = {
    bucket       = "acme-operations-0000--terraform-state"
    key          = "operations/terraform.tfstate"
    region       = "us-east-1"
    use_lockfile = true

    assume_role = {
      role_arn = "arn:aws:iam::000000000000:role/terraform"
    }
  }
}

module "environment" {
  source = "../../modules/environment"

  account_id = data.terraform_remote_state.operations.outputs.account_id
}

locals {
  feature_environment = module.environment.settings.feature_environment
  account_id          = module.environment.settings.account_id
  is_production       = terraform.workspace == "default"
  vpc_id              = data.terraform_remote_state.operations.outputs.vpc_id
  public_subnet_ids   = data.terraform_remote_state.operations.outputs.public_subnet_ids
  private_subnet_ids  = data.terraform_remote_state.operations.outputs.private_subnet_ids
  cluster_arn         = data.terraform_remote_state.operations.outputs.ecs_cluster_arn
  cluster_name        = data.terraform_remote_state.operations.outputs.ecs_cluster_name
  hosted_zone_id      = data.terraform_remote_state.operations.outputs.hosted_zone_id
}
