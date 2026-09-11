variable "project_id" {
  type        = string
  description = "ID of the GCP project where resources will be created."
}

variable "domain_name" {
  type        = string
  description = "Primary domain name for the static site (e.g., 'mentionai.app')."
}

variable "bucket_name" {
  type        = string
  description = "Name of the Cloud Storage bucket for hosting static files."
}

variable "site_files_path" {
  type        = string
  description = "Local path to static files directory (relative to module root)."
}

variable "additional_domains" {
  type        = list(string)
  description = "Additional domains to include in SSL certificate (e.g., ['www.mentionai.app'])."
  default     = []
}

variable "location" {
  type        = string
  description = "Location for the Cloud Storage bucket."
  default     = "US"
}

variable "main_page_suffix" {
  type        = string
  description = "Default page filename for directory requests."
  default     = "index.html"
}

variable "not_found_page" {
  type        = string
  description = "404 error page filename."
  default     = "404.html"
}

variable "clean_url_mappings" {
  type        = map(string)
  description = "Map of clean URLs to actual file paths (e.g., {'/pricing' = '/pricing.html'})."
  default     = {}
}

variable "enable_directory_index" {
  type        = bool
  description = "Enable automatic index.html serving for directory paths."
  default     = true
}

variable "dns_managed_zone" {
  type        = string
  description = "Name of the Cloud DNS managed zone (required if manage_dns is true)."
  default     = ""
}

variable "force_destroy" {
  type        = bool
  description = "Allow Terraform to destroy the bucket even if it contains objects."
  default     = true
}

variable "cors_origins" {
  type        = list(string)
  description = "List of origins allowed for CORS requests."
  default     = ["*"]
}

variable "cors_methods" {
  type        = list(string)
  description = "List of HTTP methods allowed for CORS requests."
  default     = ["GET", "HEAD", "OPTIONS"]
}

variable "cors_response_headers" {
  type        = list(string)
  description = "List of headers allowed in CORS responses."
  default     = ["Content-Type", "Cache-Control"]
}

variable "cors_max_age_seconds" {
  type        = number
  description = "Maximum age in seconds for CORS preflight responses."
  default     = 3600
}

variable "enable_cache_invalidation" {
  type        = bool
  description = "Enable automatic cache invalidation after file uploads."
  default     = false
}

variable "cache_invalidation_paths" {
  type        = list(string)
  description = "List of paths to invalidate. Use ['/*'] to invalidate everything."
  default     = ["/*"]
}

variable "cdn_default_ttl" {
  type        = number
  description = "Default TTL for CDN cache in seconds. Lower values = faster updates, higher costs."
  default     = 86400 # 1 day
}

variable "cdn_max_ttl" {
  type        = number
  description = "Maximum TTL for CDN cache in seconds."
  default     = 31536000 # 1 year
}

variable "cdn_client_ttl" {
  type        = number
  description = "Client TTL for CDN cache in seconds."
  default     = 86400 # 1 day
} 
