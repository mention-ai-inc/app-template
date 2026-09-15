locals {
  production = {
    resource_group_name = var.production_resource_group_name
    feature_environment = ""
    tokens = {
      clerk_publishable_key = "pk_live_REPLACE_ME"
    }
  }
}
