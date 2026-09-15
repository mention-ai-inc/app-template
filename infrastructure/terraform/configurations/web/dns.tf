resource "aws_route53_record" "vercel" {
  zone_id = local.hosted_zone_id
  name    = "${local.feature_environment}${var.app_domain}"
  type    = "CNAME"
  ttl     = 300
  records = ["cname.vercel-dns.com"]
}
