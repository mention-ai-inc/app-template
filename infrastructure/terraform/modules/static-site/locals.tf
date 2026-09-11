# Local values for the static-site module
locals {
  # All domains (primary + additional)
  all_domains = concat([var.domain_name], var.additional_domains)

  # Site files discovered from the specified path
  site_files = fileset(var.site_files_path, "**")

  # Hash of all files for tracking changes
  files_hash = md5(join("", [for file in local.site_files : filemd5("${var.site_files_path}/${file}")]))

  # MIME type mappings for common file extensions
  mime_types = {
    "html" = "text/html"
    "htm"  = "text/html"
    "css"  = "text/css"
    "js"   = "application/javascript"
    "json" = "application/json"
    "xml"  = "application/xml"
    "txt"  = "text/plain"
    "md"   = "text/markdown"

    # Images
    "jpg"  = "image/jpeg"
    "jpeg" = "image/jpeg"
    "png"  = "image/png"
    "gif"  = "image/gif"
    "webp" = "image/webp"
    "svg"  = "image/svg+xml"
    "ico"  = "image/x-icon"

    # Fonts
    "woff"  = "font/woff"
    "woff2" = "font/woff2"
    "ttf"   = "font/ttf"
    "eot"   = "application/vnd.ms-fontobject"

    # Documents
    "pdf" = "application/pdf"
    "zip" = "application/zip"

    # Default
    "" = "application/octet-stream"
  }
} 