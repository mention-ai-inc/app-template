locals {
  feature = {
    resource_group_name = var.feature_resource_group_name
    feature_environment = "${replace(terraform.workspace, "/[^a-zA-Z0-9]/", "")}"
    tokens = {
      clerk_jwks_url        = "https://feature.clerk.example.com/.well-known/jwks.json"
      clerk_publishable_key = "pk_test_REPLACE_ME"
    }
  }
}
