resource "azurerm_cdn_frontdoor_profile" "production" {
  name                     = var.production_front_door_profile_name
  resource_group_name      = azurerm_resource_group.production.name
  sku_name                 = var.front_door_sku_name
  response_timeout_seconds = var.front_door_response_timeout_seconds
}

resource "azurerm_cdn_frontdoor_profile" "feature" {
  name                     = var.feature_front_door_profile_name
  resource_group_name      = azurerm_resource_group.feature.name
  sku_name                 = var.front_door_sku_name
  response_timeout_seconds = var.front_door_response_timeout_seconds
}

output "production_front_door_profile_id" {
  value = azurerm_cdn_frontdoor_profile.production.id
}

output "production_front_door_resource_guid" {
  description = "The value Front Door sends in the X-Azure-FDID header. An origin rejects any request that does not carry it, because a Container App's own hostname is otherwise reachable directly."
  value       = azurerm_cdn_frontdoor_profile.production.resource_guid
}

output "feature_front_door_profile_id" {
  value = azurerm_cdn_frontdoor_profile.feature.id
}

output "feature_front_door_resource_guid" {
  description = "The value Front Door sends in the X-Azure-FDID header for feature environments."
  value       = azurerm_cdn_frontdoor_profile.feature.resource_guid
}
