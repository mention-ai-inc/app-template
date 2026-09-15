locals {
  terraform_role_arn = "arn:aws:iam::000000000000:role/terraform"
}

provider "aws" {
  region = var.preferred_region

  assume_role {
    role_arn     = local.terraform_role_arn
    session_name = "terraform-operations"
  }

  default_tags {
    tags = {
      Repository    = var.github_repo
      Configuration = "operations"
      Environment   = "operations"
      ManagedBy     = "terraform"
    }
  }
}

terraform {
  backend "s3" {
    bucket               = "acme-operations-0000--terraform-state"
    key                  = "operations/terraform.tfstate"
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
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

data "aws_caller_identity" "current" {}

locals {
  account_id         = data.aws_caller_identity.current.account_id
  bucket_name_prefix = var.bucket_name_prefix
}
