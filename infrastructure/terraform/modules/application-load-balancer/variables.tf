variable "feature_environment" {
  type        = string
  description = "The environment-specific prefix to use when naming resources and the hostname it serves."
}

variable "surface_name" {
  type        = string
  description = "The surface the load balancer fronts: api, mcp, or admin. Not a display name; it is used in resource names."
}

variable "domain_name" {
  type        = string
  description = "Domain name the load balancer serves, without the feature environment prefix."
}

variable "hosted_zone_id" {
  type        = string
  description = "Route 53 hosted zone the certificate is validated in and the alias record is created in."
}

variable "vpc_id" {
  type        = string
  description = "The VPC the load balancer and its target groups belong to."
}

variable "subnet_ids" {
  type        = list(string)
  description = "The public subnets the load balancer's nodes are placed in."
}

variable "rest_services" {
  type = map(object({
    target_group_name                = string
    container_port                   = number
    health_check_request_path        = string
    deregistration_delay_seconds     = number
    health_check_interval_seconds    = number
    health_check_timeout_seconds     = number
    health_check_healthy_threshold   = number
    health_check_unhealthy_threshold = number
  }))
  description = "Services reachable under /rest/<name>/*, each getting a target group the load balancer owns."
  default     = {}
}

variable "default_target_group_arn" {
  type        = string
  description = "Target group that serves every request no listener rule matches. When empty the listener answers with a 404 instead."
  default     = ""
}

variable "idle_timeout_seconds" {
  type        = number
  description = "Seconds the load balancer keeps an idle connection open."
  default     = 60
}

variable "ingress_cidr_blocks" {
  type        = list(string)
  description = "Address ranges allowed to reach the load balancer."
  default     = ["0.0.0.0/0"]
}

variable "deletion_protection_enabled" {
  type        = bool
  description = "Whether the load balancer refuses to be deleted. Production only, so feature environments stay destroyable."
  default     = false
}

variable "authenticate_oidc" {
  type = object({
    issuer                 = string
    authorization_endpoint = string
    token_endpoint         = string
    user_info_endpoint     = string
    client_id              = string
    client_secret          = string
    scope                  = string
    session_timeout        = number
  })
  description = "OIDC provider the listener authenticates every request against before forwarding it. Null leaves the surface unauthenticated at the edge."
  default     = null
  sensitive   = true
}

variable "web_acl_arn" {
  type        = string
  description = "ARN of a WAF web ACL to associate with the load balancer."
  default     = ""
}

variable "access_log_bucket" {
  type        = string
  description = "Bucket the load balancer writes access logs to. Empty disables access logging."
  default     = ""
}
