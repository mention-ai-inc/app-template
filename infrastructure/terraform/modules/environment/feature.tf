locals {
  feature = {
    project_id          = var.feature_project_id
    feature_environment = "${replace(terraform.workspace, "/[^a-zA-z0-9]/", "")}"
    tokens = {
      clerk_publishable_key = "pk_test_cHJlY2lvdXMtamF2ZWxpbi0xNS5jbGVyay5hY2NvdW50cy5kZXYk"
    }
  }
}
