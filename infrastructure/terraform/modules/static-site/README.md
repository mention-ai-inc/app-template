# Static Site Terraform Module

This Terraform module creates a complete static website hosting solution on Google Cloud Platform using:

- Cloud Storage bucket with website configuration
- Global Load Balancer with SSL termination
- Automatic file uploads from local directory
- Clean URL support (e.g., `/pricing` instead of `/pricing.html`)
- Optional Cloud CDN integration
- Optional DNS management
- HTTP to HTTPS redirects

## Features

- ✅ **Automatic file uploads** - Discovers and uploads all files from specified directory
- ✅ **Clean URLs** - Configure custom URL mappings (e.g., `/about` → `/about.html`)
- ✅ **HTTPS with SSL** - Google-managed SSL certificates for all domains
- ✅ **Multi-domain support** - Support for `example.com` and `www.example.com`
- ✅ **Global CDN** - Optional Cloud CDN for improved performance
- ✅ **DNS management** - Optional creation of DNS A records
- ✅ **HTTP redirects** - Automatic HTTP to HTTPS redirects

## Usage

### Basic Example

```hcl
module "my_static_site" {
  source = "../../modules/static-site"
  
  project_id      = "my-project-id"
  domain_name     = "example.com"
  bucket_name     = "my-project-static-site"
  site_files_path = "../../../../apps/my-site"
}
```

### Advanced Example with Clean URLs and DNS

```hcl
module "landing_page" {
  source = "../../modules/static-site"
  
  project_id         = "my-project-id"
  domain_name        = "acme.example.com"
  additional_domains = ["www.acme.example.com"]
  bucket_name        = "my-project-landing-page"
  site_files_path    = "../../../../apps/landing"
  
  # Clean URL mappings
  clean_url_mappings = {
    "/pricing" = "/pricing.html"
    "/about"   = "/about.html"
    "/contact" = "/contact.html"
  }
  
  # DNS management
  dns_managed_zone = "acme"
}
```

## Requirements

| Name | Version |
|------|---------|
| terraform | >= 1.0 |
| google | >= 4.0 |

## Providers

| Name | Version |
|------|---------|
| google | >= 4.0 |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| project_id | ID of the GCP project where resources will be created | `string` | n/a | yes |
| domain_name | Primary domain name for the static site | `string` | n/a | yes |
| bucket_name | Name of the Cloud Storage bucket for hosting static files | `string` | n/a | yes |
| site_files_path | Local path to static files directory (relative to module root) | `string` | n/a | yes |
| additional_domains | Additional domains to include in SSL certificate | `list(string)` | `[]` | no |
| location | Location for the Cloud Storage bucket | `string` | `"US"` | no |
| main_page_suffix | Default page filename for directory requests | `string` | `"index.html"` | no |
| not_found_page | 404 error page filename | `string` | `"404.html"` | no |
| clean_url_mappings | Map of clean URLs to actual file paths | `map(string)` | `{}` | no |
| enable_directory_index | Enable automatic index.html serving for directory paths | `bool` | `true` | no |
| manage_dns | Whether to create DNS A records for the domains | `bool` | `false` | no |
| dns_managed_zone | Name of the Cloud DNS managed zone | `string` | `""` | no |
| enable_cdn | Enable Cloud CDN for the backend bucket | `bool` | `false` | no |

## Outputs

| Name | Description |
|------|-------------|
| bucket_name | Name of the Cloud Storage bucket |
| load_balancer_ip | IP address of the load balancer |
| site_urls | HTTPS URLs for all configured domains |
| ssl_certificate_status | Status of the SSL certificate |
| uploaded_files_count | Number of files uploaded to the bucket |

## SSL Certificate Provisioning

⚠️ **Important**: SSL certificate provisioning can take 60-90 minutes. The certificate status can be monitored using:

```bash
# Check certificate status
gcloud certificate-manager certificates describe <certificate-name> --global

# Check domain validation status
gcloud certificate-manager certificates describe <certificate-name> --global --format="get(managed.domainStatus)"
```

## File Structure Requirements

Your static site files should be organized in a directory structure like:

```
apps/my-site/
├── index.html
├── 404.html
├── pricing.html
├── about.html
├── styles.css
├── assets/
│   ├── logo.png
│   └── background.jpg
└── js/
    └── app.js
```

## Clean URL Configuration

Configure clean URLs by mapping clean paths to actual files:

```hcl
clean_url_mappings = {
  "/pricing"    = "/pricing.html"
  "/about"      = "/about.html"
  "/contact"    = "/contact.html"
  "/blog"       = "/blog/index.html"
  "/docs"       = "/documentation.html"
}
```

This enables:
- `https://example.com/pricing` → serves `pricing.html`
- `https://example.com/about` → serves `about.html`
- `https://example.com/` → serves `index.html`

## Notes

- The module automatically detects and uploads all files from the specified directory
- MIME types are automatically detected based on file extensions
- Cache headers are optimized for performance (5 minutes for HTML, 24 hours for assets)
- HTTP traffic is automatically redirected to HTTPS
- The load balancer provides global distribution and DDoS protection

## Cache Invalidation

When deploying changes to your static site, you may want them to be visible immediately rather than waiting for the cache to expire. This module provides two approaches:

### Option 1: Automatic Cache Invalidation (Recommended)

Enable automatic cache invalidation after file uploads:

```hcl
module "my_static_site" {
  source = "../../modules/static-site"
  
  # ... other configuration ...
  
  # Enable automatic cache invalidation
  enable_cache_invalidation = true
  cache_invalidation_paths  = ["/*"]  # Invalidate everything, or specify specific paths
}
```

This will automatically invalidate the CDN cache whenever files change during `terraform apply`.

### Option 2: Reduced Cache TTL

For immediate updates without cache invalidation, reduce the cache TTL:

```hcl
module "my_static_site" {
  source = "../../modules/static-site"
  
  # ... other configuration ...
  
  # Faster updates but higher costs and reduced performance
  cdn_default_ttl = 300    # 5 minutes instead of 1 day
  cdn_client_ttl  = 300    # 5 minutes instead of 1 day
  cdn_max_ttl     = 3600   # 1 hour instead of 1 year
}
```

### Manual Cache Invalidation

Use the provided CLI script for manual cache invalidation:

```bash
# Invalidate everything
./infrastructure/cli/invalidate-landing-cache

# Invalidate specific paths
./infrastructure/cli/invalidate-landing-cache /pricing /about
```

**Note**: Cache invalidation in Google Cloud CDN typically takes 30-60 seconds to propagate globally. 