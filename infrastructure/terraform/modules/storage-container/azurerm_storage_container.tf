resource "azurerm_storage_container" "container" {
  name               = join("", [var.feature_environment, var.service != "" ? "${var.service}-" : "", var.container_name])
  storage_account_id = var.storage_account_id
}
