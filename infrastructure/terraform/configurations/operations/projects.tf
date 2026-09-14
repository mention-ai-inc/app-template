module "production-project" {
  source = "../../modules/project"

  project_name       = "Acme Production"
  project_id_base    = "acme-production"
  random_project_id  = "true"
  organization_id    = var.organization_id
  folder_id          = var.folder_id
  billing_account_id = var.billing_account_id
  gcp_services       = var.gcp_services
  firebase           = true
}

module "feature-project" {
  source = "../../modules/project"

  project_name       = "Acme Feature"
  project_id_base    = "acme-feature"
  random_project_id  = "true"
  organization_id    = var.organization_id
  folder_id          = var.folder_id
  billing_account_id = var.billing_account_id
  gcp_services       = var.gcp_services
  firebase           = true
}

output "production_project_id" {
  value = module.production-project.project_id
}

output "feature_project_id" {
  value = module.feature-project.project_id
}

output "production_project_number" {
  value = module.production-project.project_number
}

output "feature_project_number" {
  value = module.feature-project.project_number
}
