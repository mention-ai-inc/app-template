locals {
  terraform_service_account = "terraform@acme-operations-155d.iam.gserviceaccount.com"
}

# cloud providers
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
  target_service_account = local.terraform_service_account
  lifetime               = "1200s"
}

provider "google" {
  project         = var.operations_project_id
  access_token    = data.google_service_account_access_token.default.access_token
  request_timeout = "60s"
}

# remote terraform state store
terraform {
  backend "gcs" {
    bucket                      = "acme-operations-155d--terraform-state"
    prefix                      = "operations"
    impersonate_service_account = "terraform@acme-operations-155d.iam.gserviceaccount.com"
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">=6.0.0"
    }
  }
}
