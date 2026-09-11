# Upload all site files to the bucket
resource "google_storage_bucket_object" "site_files" {
  for_each = local.site_files

  bucket = google_storage_bucket.site.name
  name   = each.value
  source = "${var.site_files_path}/${each.value}"

  # Determine content type based on file extension
  content_type = lookup(
    local.mime_types,
    length(split(".", each.value)) > 1 ? split(".", each.value)[length(split(".", each.value)) - 1] : "",
    "application/octet-stream"
  )

  # Cache control headers for better performance
  cache_control = each.value == var.main_page_suffix ? "public, max-age=300" : "public, max-age=86400"

  # Static metadata (no dynamic timestamps)
  metadata = {
    uploaded_by = "terraform-static-site-module"
    managed_by  = "terraform"
  }

  depends_on = [google_storage_bucket.site]
}

# Cache invalidation after file uploads
resource "null_resource" "cache_invalidation" {
  count = var.enable_cache_invalidation ? 1 : 0

  # Trigger cache invalidation whenever files change
  triggers = {
    files_hash = local.files_hash
  }

  provisioner "local-exec" {
    command = <<-EOT
      echo "Invalidating CDN cache for URL map: ${google_compute_url_map.url_map.name}"
      gcloud compute url-maps invalidate-cdn-cache ${google_compute_url_map.url_map.name} \
        --path="${join(",", var.cache_invalidation_paths)}" \
        --global \
        --project=${var.project_id} \
        --quiet
    EOT
  }

  depends_on = [
    google_storage_bucket_object.site_files,
    google_compute_url_map.url_map
  ]
} 