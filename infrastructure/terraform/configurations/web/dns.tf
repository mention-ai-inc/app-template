resource "azurerm_dns_cname_record" "vercel" {
  name                = "${local.feature_environment}app"
  zone_name           = local.dns_zone_name
  resource_group_name = local.dns_zone_resource_group_name
  ttl                 = 300
  record              = "cname.vercel-dns.com."
}
