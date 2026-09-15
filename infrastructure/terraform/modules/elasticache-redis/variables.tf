variable "name" {
  type        = string
  description = "Name of the replication group, carrying the feature environment prefix."
}

variable "subnet_ids" {
  type        = list(string)
  description = "Private subnets the cache nodes are placed in."
}

variable "vpc_id" {
  type        = string
  description = "VPC the cache and its security group belong to."
}

variable "allowed_security_group_ids" {
  type        = list(string)
  description = "Security groups allowed to reach the cache on its port."
  default     = []
}

variable "allowed_cidr_blocks" {
  type        = list(string)
  description = "Address ranges allowed to reach the cache on its port. The cache has no public endpoint, so this is the VPC's own range rather than anything routable from outside it."
  default     = []
}

variable "node_type" {
  type        = string
  description = "Instance class of the cache nodes."
  default     = "cache.t4g.micro"
}

variable "engine_version" {
  type        = string
  description = "Redis engine version."
  default     = "7.1"
}

variable "maximum_memory_policy" {
  type        = string
  description = "Eviction policy applied once the cache reaches its memory limit."
  default     = "allkeys-lru"
}

variable "port" {
  type        = number
  description = "Port the cache listens on."
  default     = 6379
}

variable "is_production" {
  type        = bool
  description = "Whether the cache belongs to production, which turns on multi-AZ failover and daily snapshots."
}

variable "auth_token" {
  type        = string
  description = "Password required by clients connecting to the cache."
  sensitive   = true
}
