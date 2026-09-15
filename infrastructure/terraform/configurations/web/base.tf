locals {
  terraform_role_arn = "arn:aws:iam::000000000000:role/terraform"
}

provider "aws" {
  region = var.preferred_region

  assume_role {
    role_arn     = local.terraform_role_arn
    session_name = "terraform-web"
  }

  default_tags {
    tags = {
      Repository    = var.github_repo
      Configuration = "web"
      Environment   = terraform.workspace
      ManagedBy     = "terraform"
    }
  }
}

data "aws_secretsmanager_secret_version" "vercel-api-token" {
  secret_id = "VERCEL_TERRAFORM_API_KEY"
}

provider "vercel" {
  api_token = data.aws_secretsmanager_secret_version.vercel-api-token.secret_string
  team      = var.vercel_team_id
}

terraform {
  backend "s3" {
    bucket               = "acme-operations-0000--terraform-state"
    key                  = "web/terraform.tfstate"
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
    vercel = {
      source  = "vercel/vercel"
      version = "2.8.0"
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
  hosted_zone_id      = data.terraform_remote_state.operations.outputs.hosted_zone_id
}
