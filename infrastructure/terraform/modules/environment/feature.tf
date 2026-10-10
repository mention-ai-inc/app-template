locals {
  feature = {
    project_id          = var.feature_project_id
    feature_environment = "${replace(terraform.workspace, "/[^a-zA-z0-9]/", "")}"
    tokens = {
      clerk_jwks_url        = "https://feature.clerk.example.com/.well-known/jwks.json"
      clerk_publishable_key = "pk_test_REPLACE_ME"
    }
  }
}
