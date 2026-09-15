resource "azurerm_cdn_frontdoor_origin" "service" {
  for_each = var.rest_service_origins

  name                          = "${var.feature_environment}${replace(each.key, "_", "-")}"
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.service[each.key].id
  enabled                       = true

  host_name                      = each.value
  origin_host_header             = each.value
  https_port                     = 443
  http_port                      = 80
  priority                       = 1
  weight                         = 1000
  certificate_name_check_enabled = true
}

resource "azurerm_cdn_frontdoor_origin" "catchall" {
  name                          = "${var.feature_environment}catchall"
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.catchall.id
  enabled                       = true

  host_name                      = module.catchall-server.fqdn
  origin_host_header             = module.catchall-server.fqdn
  https_port                     = 443
  http_port                      = 80
  priority                       = 1
  weight                         = 1000
  certificate_name_check_enabled = true
}
