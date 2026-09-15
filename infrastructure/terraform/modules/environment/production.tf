locals {
  production = {
    account_id          = var.account_id
    feature_environment = ""
    tokens = {
      clerk_publishable_key = "pk_live_REPLACE_ME"
    }
  }
}
