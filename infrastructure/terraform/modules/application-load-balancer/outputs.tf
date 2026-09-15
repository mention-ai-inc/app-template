output "dns_name" {
  description = "The load balancer's own hostname, which the alias record points at."
  value       = aws_lb.load-balancer.dns_name
}

output "fqdn" {
  description = "The hostname the surface is served on."
  value       = local.fqdn
}

output "arn" {
  description = "ARN of the load balancer."
  value       = aws_lb.load-balancer.arn
}

output "security_group_id" {
  description = "Security group of the load balancer, which target services allow ingress from."
  value       = aws_security_group.load-balancer.id
}

output "https_listener_arn" {
  description = "ARN of the HTTPS listener, which extra rules attach to."
  value       = aws_lb_listener.https.arn
}

output "target_group_arns" {
  description = "Target group ARN per service, for the service that registers into it."
  value       = { for service_name, group in aws_lb_target_group.rest : service_name => group.arn }
}
