module "project-factory" {
  source  = "terraform-google-modules/project-factory/google"
  version = "~> 18.1"

  name              = var.project_name
  random_project_id = var.random_project_id
  project_id        = var.project_id_base
  org_id            = var.organization_id
  folder_id         = var.folder_id
  billing_account   = var.billing_account_id
  activate_apis     = var.gcp_services
}
