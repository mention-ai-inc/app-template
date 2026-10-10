resource "azurerm_cosmosdb_sql_container" "leases" {
  name                = "${var.service_name}-${replace(var.trigger_name, "_", "-")}-leases"
  resource_group_name = var.resource_group_name
  account_name        = var.cosmos_account_name
  database_name       = var.cosmos_database_name
  partition_key_paths = ["/id"]

  dynamic "autoscale_settings" {
    for_each = var.provisioned_throughput ? [1] : []

    content {
      max_throughput = var.max_throughput
    }
  }
}
