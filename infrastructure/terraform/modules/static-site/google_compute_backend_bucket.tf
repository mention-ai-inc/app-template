resource "google_compute_backend_bucket" "backend" {
  project     = var.project_id
  name        = "${var.bucket_name}-backend"
  description = "Backend bucket for ${var.domain_name} static site"
  bucket_name = google_storage_bucket.site.name
  enable_cdn  = true

  # CDN policy configuration
  cdn_policy {
    cache_mode       = "CACHE_ALL_STATIC"
    default_ttl      = var.cdn_default_ttl
    max_ttl          = var.cdn_max_ttl
    client_ttl       = var.cdn_client_ttl
    negative_caching = true

    negative_caching_policy {
      code = 404
      ttl  = 300 # 5 minutes for 404s
    }
  }
} 