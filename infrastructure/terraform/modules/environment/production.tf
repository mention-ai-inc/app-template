locals {
  production = {
    resource_group_name = var.production_resource_group_name
    feature_environment = ""
    tokens = {
      clerk_jwks_url        = "https://production.clerk.example.com/.well-known/jwks.json"
      clerk_publishable_key = "pk_live_REPLACE_ME"
    }
  }
}
