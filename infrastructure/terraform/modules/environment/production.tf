locals {
  production = {
    project_id          = var.production_project_id
    feature_environment = ""
    tokens = {
      clerk_publishable_key = "pk_live_REPLACE_ME"
    }
  }
}
