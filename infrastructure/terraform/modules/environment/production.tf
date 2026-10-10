locals {
  production = {
    project_id          = var.production_project_id
    feature_environment = ""
    tokens = {
      clerk_jwks_url        = "https://production.clerk.example.com/.well-known/jwks.json"
      clerk_publishable_key = "pk_live_REPLACE_ME"
    }
  }
}
