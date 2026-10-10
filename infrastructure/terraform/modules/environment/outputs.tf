output "settings" {
  value = local.environments[terraform.workspace == "default" ? "production" : "feature"]
}
