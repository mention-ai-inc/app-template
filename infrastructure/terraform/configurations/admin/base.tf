provider "google" {
  alias = "impersonation"
  scopes = [
    "https://www.googleapis.com/auth/cloud-platform",
    "https://www.googleapis.com/auth/userinfo.email",
  ]
}

data "google_service_account_access_token" "default" {
  provider               = google.impersonation
  scopes                 = ["userinfo-email", "cloud-platform"]
  target_service_account = "terraform@acme-operations-155d.iam.gserviceaccount.com"
  lifetime               = "1200s"
}

provider "google" {
  project         = var.operations_project_id
  access_token    = data.google_service_account_access_token.default.access_token
  request_timeout = "60s"
}

terraform {
  backend "gcs" {
    bucket = "acme-operations-155d--terraform-state"
    prefix = "admin"
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">=6.0.0"
    }
  }
}

module "environment" {
  source = "../../modules/environment"

  feature_project_id    = data.terraform_remote_state.operations.outputs.feature_project_id
  production_project_id = data.terraform_remote_state.operations.outputs.production_project_id
}

locals {
  feature_environment = module.environment.settings.feature_environment
  project             = module.environment.settings.project_id
  is_production       = terraform.workspace == "default"
  project_number      = terraform.workspace == "default" ? data.terraform_remote_state.operations.outputs.production_project_number : data.terraform_remote_state.operations.outputs.feature_project_number
}

data "terraform_remote_state" "operations" {
  backend   = "gcs"
  workspace = "default"

  config = {
    bucket = "acme-operations-155d--terraform-state"
    prefix = "operations"
  }
}

data "terraform_remote_state" "services" {
  backend   = "gcs"
  workspace = terraform.workspace

  config = {
    bucket = "acme-operations-155d--terraform-state"
    prefix = "services"
  }
}
