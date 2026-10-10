resource "azurerm_cdn_frontdoor_custom_domain_association" "api" {
  cdn_frontdoor_custom_domain_id = azurerm_cdn_frontdoor_custom_domain.api.id

  cdn_frontdoor_route_ids = concat(
    [for route in azurerm_cdn_frontdoor_route.service : route.id],
    [azurerm_cdn_frontdoor_route.catchall.id],
  )
}
