locals {
  mcp_fqdn = "${local.feature_environment}${var.mcp_subdomain}.${var.domain_name}"
  api_url  = "https://${local.feature_environment}api.${var.domain_name}"
}

# Clerk acts as the OAuth authorization server for the MCP server. `@clerk/mcp-tools`
# validates the incoming Clerk OAuth access token and serves the OAuth metadata using
# this secret key (the key also determines which Clerk instance — dev vs production).

data "google_secret_manager_secret_version_access" "clerk-secret-key" {
  project = local.project
  secret  = "CLERK_SECRET_KEY"
}

# service account

module "mcp-service-account" {
  source = "../../modules/service-account"

  project_id = local.project
  account_id = "${local.feature_environment}mcpclient-s"
  roles = [
    "roles/run.invoker",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
  ]
}

# cloud run service

module "mcp-server" {
  source = "../../modules/cloud-run-server"

  project_id            = local.project
  region                = var.preferred_region
  feature_environment   = local.feature_environment
  service_name          = "mcp"
  server_name           = "rest"
  service_account_email = module.mcp-service-account.email

  cpu                       = "1"
  memory                    = "512Mi"
  container_concurrency     = 80
  timeout_seconds           = 300
  minimum_instances         = 0
  maximum_instances         = 10
  health_check_request_path = "/health"
  vpc_network               = data.terraform_remote_state.operations.outputs.shared-vpc-network-id
  vpc_subnetwork            = data.terraform_remote_state.operations.outputs.cloud-run-subnetwork-id

  env = {
    API_URL               = local.api_url
    CLERK_SECRET_KEY      = data.google_secret_manager_secret_version_access.clerk-secret-key.secret_data
    CLERK_PUBLISHABLE_KEY = module.environment.settings.tokens.clerk_publishable_key
  }
}

# load balancer

resource "google_compute_global_address" "mcp-ip" {
  project      = local.project
  name         = "${local.feature_environment}mcp-global-ip-address"
  address_type = "EXTERNAL"
  ip_version   = "IPV4"
}

resource "google_certificate_manager_certificate" "mcp-ssl" {
  project = local.project
  name    = "${local.feature_environment}mcp-ssl-certificate"

  managed {
    domains = [local.mcp_fqdn]
  }
}

resource "google_certificate_manager_certificate_map" "mcp-cert-map" {
  project = local.project
  name    = "${local.feature_environment}mcp-certificate-map"
}

resource "google_certificate_manager_certificate_map_entry" "mcp-cert-map-entry" {
  project      = local.project
  name         = "${local.feature_environment}mcp-certificate-map-entry"
  map          = google_certificate_manager_certificate_map.mcp-cert-map.name
  certificates = [google_certificate_manager_certificate.mcp-ssl.id]
  hostname     = local.mcp_fqdn
}

resource "google_compute_url_map" "mcp-url-map" {
  project         = local.project
  name            = "${local.feature_environment}mcp-url-map"
  default_service = module.mcp-server.backend_service_self_link
}

resource "google_compute_target_https_proxy" "mcp-https-proxy" {
  project         = local.project
  name            = "${local.feature_environment}mcp-target-https-proxy"
  certificate_map = "//certificatemanager.googleapis.com/${google_certificate_manager_certificate_map.mcp-cert-map.id}"
  url_map         = google_compute_url_map.mcp-url-map.self_link
}

resource "google_compute_global_forwarding_rule" "mcp-forwarding-rule" {
  project               = local.project
  name                  = "${local.feature_environment}mcp-forwarding-rule"
  target                = google_compute_target_https_proxy.mcp-https-proxy.self_link
  port_range            = "443-443"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  ip_address            = google_compute_global_address.mcp-ip.id
}

# dns

resource "google_dns_record_set" "mcp" {
  name         = "${local.mcp_fqdn}."
  type         = "A"
  ttl          = 300
  managed_zone = var.dns_managed_zone
  rrdatas      = [google_compute_global_address.mcp-ip.address]
}
