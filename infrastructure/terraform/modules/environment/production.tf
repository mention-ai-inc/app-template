locals {
  production = {
    account_id          = var.account_id
    feature_environment = ""
    tokens = {
      clerk_jwks_url        = "https://production.clerk.example.com/.well-known/jwks.json"
      clerk_publishable_key = "pk_live_REPLACE_ME"
    }
  }
}
