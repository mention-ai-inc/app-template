resource "azurerm_container_app_environment_managed_certificate" "server" {
  count = local.has_custom_domain ? 1 : 0

  name                         = module.container-app-name.name
  container_app_environment_id = var.container_app_environment_id
  subject_name                 = var.custom_domain_fqdn
  domain_control_validation    = "CNAME"

  depends_on = [
    azurerm_dns_cname_record.server,
    azurerm_dns_txt_record.server-domain-verification,
  ]
}
