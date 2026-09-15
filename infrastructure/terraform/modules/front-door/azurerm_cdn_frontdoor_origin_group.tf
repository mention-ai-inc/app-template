resource "azurerm_cdn_frontdoor_origin_group" "service" {
  for_each = var.rest_service_origins

  name                                                      = "${var.feature_environment}${replace(each.key, "_", "-")}"
  cdn_frontdoor_profile_id                                  = var.profile_id
  session_affinity_enabled                                  = false
  restore_traffic_time_to_healed_or_new_endpoint_in_minutes = 0

  health_probe {
    path                = "/rest/${each.key}/health"
    protocol            = "Https"
    request_type        = "GET"
    interval_in_seconds = var.health_probe_interval_seconds
  }

  load_balancing {
    sample_size                        = 4
    successful_samples_required        = 3
    additional_latency_in_milliseconds = 50
  }
}

resource "azurerm_cdn_frontdoor_origin_group" "catchall" {
  name                                                      = "${var.feature_environment}catchall"
  cdn_frontdoor_profile_id                                  = var.profile_id
  session_affinity_enabled                                  = false
  restore_traffic_time_to_healed_or_new_endpoint_in_minutes = 0

  health_probe {
    path                = "/"
    protocol            = "Https"
    request_type        = "HEAD"
    interval_in_seconds = var.health_probe_interval_seconds
  }

  load_balancing {
    sample_size                        = 4
    successful_samples_required        = 3
    additional_latency_in_milliseconds = 50
  }
}
