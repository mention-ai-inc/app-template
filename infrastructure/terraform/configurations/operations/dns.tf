resource "aws_route53_zone" "zone" {
  name          = var.domain_name
  comment       = "DNS zone for ${var.domain_name}."
  force_destroy = false
}

output "hosted_zone_id" {
  value = aws_route53_zone.zone.zone_id
}

output "hosted_zone_name_servers" {
  value = aws_route53_zone.zone.name_servers
}

output "domain_name" {
  value = var.domain_name
}
