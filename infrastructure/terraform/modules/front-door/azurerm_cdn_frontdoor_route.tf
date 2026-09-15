resource "azurerm_cdn_frontdoor_route" "service" {
  for_each = var.rest_service_origins

  name                          = "${var.feature_environment}${replace(each.key, "_", "-")}"
  cdn_frontdoor_endpoint_id     = azurerm_cdn_frontdoor_endpoint.api.id
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.service[each.key].id
  cdn_frontdoor_origin_ids      = [azurerm_cdn_frontdoor_origin.service[each.key].id]
  enabled                       = true

  patterns_to_match   = ["/rest/${each.key}", "/rest/${each.key}/*"]
  supported_protocols = ["Http", "Https"]
  forwarding_protocol = "HttpsOnly"

  https_redirect_enabled = true
  link_to_default_domain = true

  cdn_frontdoor_custom_domain_ids = [azurerm_cdn_frontdoor_custom_domain.api.id]

  cache {
    query_string_caching_behavior = "UseQueryString"
    compression_enabled           = false
  }
}

resource "azurerm_cdn_frontdoor_route" "catchall" {
  name                          = "${var.feature_environment}catchall"
  cdn_frontdoor_endpoint_id     = azurerm_cdn_frontdoor_endpoint.api.id
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.catchall.id
  cdn_frontdoor_origin_ids      = [azurerm_cdn_frontdoor_origin.catchall.id]
  enabled                       = true

  patterns_to_match   = ["/*"]
  supported_protocols = ["Http", "Https"]
  forwarding_protocol = "HttpsOnly"

  https_redirect_enabled = true
  link_to_default_domain = true

  cdn_frontdoor_custom_domain_ids = [azurerm_cdn_frontdoor_custom_domain.api.id]

  cache {
    query_string_caching_behavior = "UseQueryString"
    compression_enabled           = false
  }
}
