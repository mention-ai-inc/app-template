resource "azurerm_container_app_custom_domain" "server" {
  count = local.has_custom_domain ? 1 : 0

  name                                     = var.custom_domain_fqdn
  container_app_id                         = azurerm_container_app.server.id
  container_app_environment_certificate_id = azurerm_container_app_environment_managed_certificate.server[0].id
  certificate_binding_type                 = "SniEnabled"
}
