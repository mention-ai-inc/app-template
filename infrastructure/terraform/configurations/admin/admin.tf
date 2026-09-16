locals {
  admin_fqdn = "${local.feature_environment}${var.admin_subdomain}.${var.domain_name}"

  env_variables = {
    "CLERK_JWKS_URL"       = module.environment.settings.tokens.clerk_jwks_url
    "GOOGLE_CLOUD_PROJECT" = local.project
    "FEATURE_ENVIRONMENT"  = local.feature_environment
    "PYTHONWARNINGS"       = var.python_warnings
    "REDIS_HOST"           = data.terraform_remote_state.services.outputs.redis_internal_ip

    "REDIS_PASSWORD"      = data.google_secret_manager_secret_version_access.redis-password.secret_data
    "CLERK_SECRET_KEY"    = data.google_secret_manager_secret_version_access.clerk-secret-key.secret_data
    "GEMINI_API_KEY"      = data.google_secret_manager_secret_version_access.gemini-api-key.secret_data
    "SENTRY_DSN"          = var.enable_sentry ? data.google_secret_manager_secret_version_access.sentry-dsn[0].secret_data : ""
    "LOGFIRE_WRITE_TOKEN" = var.enable_logfire ? data.google_secret_manager_secret_version_access.logfire-write-token[0].secret_data : ""
  }

  staff_allowlist = concat(
    module.permissions.engineers_members,
    local.is_production ? [] : ["terraform@acme-operations-0000.iam.gserviceaccount.com"],
  )
}

resource "google_artifact_registry_repository" "admin-docker-images" {
  description   = "This repository contains Docker images for the admin CLI."
  format        = "DOCKER"
  location      = var.preferred_region
  project       = local.project
  repository_id = "${local.feature_environment}admin"

  timeouts {}
}

module "admin-service-account" {
  source = "../../modules/service-account"

  project_id = local.project
  account_id = "${local.feature_environment}admin-s"
  roles = [
    "roles/artifactregistry.reader",
    "roles/compute.networkUser",
    "roles/compute.viewer",
    "roles/datastore.user",
    "roles/eventarc.eventReceiver",
    "roles/logging.logWriter",
    "roles/logging.viewer",
    "roles/monitoring.metricWriter",
    "roles/pubsub.publisher",
    "roles/run.developer",
    "roles/run.invoker",
    "roles/storage.objectAdmin",
  ]
  user_impersonaters = local.is_production ? [] : module.permissions.engineers_members
}

# jobs

module "admin-backfill-job" {
  source = "../../modules/cloud-run-job"

  project_id          = local.project
  project_number      = local.project_number
  region              = var.preferred_region
  feature_environment = local.feature_environment
  service_name        = "admin"
  job_name            = "backfill"

  command = ["admin", "backfill"]

  max_retries           = 0
  task_timeout          = "3600s"
  service_account_email = module.admin-service-account.email
  cpu                   = "1"
  memory                = "2Gi"
  vpc_network           = data.terraform_remote_state.operations.outputs.shared-vpc-network-id
  vpc_subnetwork        = data.terraform_remote_state.operations.outputs.cloud-run-subnetwork-id
  env                   = local.env_variables
}

module "admin-seed-job" {
  count  = local.is_production ? 0 : 1
  source = "../../modules/cloud-run-job"

  project_id          = local.project
  project_number      = local.project_number
  region              = var.preferred_region
  feature_environment = local.feature_environment
  service_name        = "admin"
  job_name            = "seed"

  command = ["admin", "seed"]

  max_retries           = 0
  task_timeout          = "21600s"
  service_account_email = module.admin-service-account.email
  cpu                   = "1"
  memory                = "2Gi"
  vpc_network           = data.terraform_remote_state.operations.outputs.shared-vpc-network-id
  vpc_subnetwork        = data.terraform_remote_state.operations.outputs.cloud-run-subnetwork-id
  env                   = local.env_variables
}

# cloud run service

resource "google_project_service_identity" "iap" {
  provider = google-beta
  project  = local.project
  service  = "iap.googleapis.com"
}

module "admin-server" {
  source = "../../modules/cloud-run-server"

  depends_on = [google_project_service_identity.iap]

  project_id            = local.project
  project_number        = local.project_number
  region                = var.preferred_region
  feature_environment   = local.feature_environment
  service_name          = "admin"
  server_name           = "rest"
  service_account_email = module.admin-service-account.email

  ingress            = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"
  public_access      = false
  iap_enabled        = true
  security_policy    = google_compute_security_policy.admin.self_link
  keep_alive_enabled = false

  cpu                       = "1"
  memory                    = "1Gi"
  container_concurrency     = 80
  timeout_seconds           = 300
  minimum_instances         = 0
  maximum_instances         = 3
  health_check_request_path = "/health"
  vpc_network               = data.terraform_remote_state.operations.outputs.shared-vpc-network-id
  vpc_subnetwork            = data.terraform_remote_state.operations.outputs.cloud-run-subnetwork-id

  env = merge(local.env_variables, {
    "SERVICE"                  = "admin"
    "IAP_BACKEND_SERVICE_NAME" = "${local.feature_environment}admin-backend-service"
    "STAFF_ALLOWLIST"          = join(",", local.staff_allowlist)
  })
}

# audit fan-out

module "admin-trigger-pool" {
  source = "../../modules/cloud-run-pool"

  project_id          = local.project
  region              = var.preferred_region
  feature_environment = local.feature_environment
  service_name        = "admin"
  pool_name           = "triggers"
  component_type      = "trigger"

  service_account_email = module.admin-service-account.email
  vpc_network           = data.terraform_remote_state.operations.outputs.shared-vpc-network-id
  vpc_subnetwork        = data.terraform_remote_state.operations.outputs.cloud-run-subnetwork-id

  env = merge(local.env_variables, {
    "SERVICE" = "admin"
  })
}

module "admin-audit-trigger" {
  source = "../../modules/eventarc-trigger"

  project_id          = local.project
  region              = var.preferred_region
  feature_environment = local.feature_environment
  service_name        = "admin"
  trigger_name        = "publish_audit_event"

  firestore_collection  = "audit"
  firestore_event_type  = "written"
  pool_cloud_run_name   = module.admin-trigger-pool.cloud_run_name
  service_account_email = module.admin-service-account.email
}

# load balancer

resource "google_compute_global_address" "admin-ip" {
  project      = local.project
  name         = "${local.feature_environment}admin-global-ip-address"
  address_type = "EXTERNAL"
  ip_version   = "IPV4"
}

resource "google_certificate_manager_certificate" "admin-ssl" {
  project = local.project
  name    = "${local.feature_environment}admin-ssl-certificate"

  managed {
    domains = [local.admin_fqdn]
  }
}

resource "google_certificate_manager_certificate_map" "admin-cert-map" {
  project = local.project
  name    = "${local.feature_environment}admin-certificate-map"
}

resource "google_certificate_manager_certificate_map_entry" "admin-cert-map-entry" {
  project      = local.project
  name         = "${local.feature_environment}admin-certificate-map-entry"
  map          = google_certificate_manager_certificate_map.admin-cert-map.name
  certificates = [google_certificate_manager_certificate.admin-ssl.id]
  hostname     = local.admin_fqdn
}

resource "google_compute_url_map" "admin-url-map" {
  project         = local.project
  name            = "${local.feature_environment}admin-url-map"
  default_service = module.admin-server.backend_service_self_link
}

resource "google_compute_target_https_proxy" "admin-https-proxy" {
  project         = local.project
  name            = "${local.feature_environment}admin-target-https-proxy"
  certificate_map = "//certificatemanager.googleapis.com/${google_certificate_manager_certificate_map.admin-cert-map.id}"
  url_map         = google_compute_url_map.admin-url-map.self_link
}

resource "google_compute_global_forwarding_rule" "admin-forwarding-rule" {
  project               = local.project
  name                  = "${local.feature_environment}admin-forwarding-rule"
  target                = google_compute_target_https_proxy.admin-https-proxy.self_link
  port_range            = "443-443"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  ip_address            = google_compute_global_address.admin-ip.id
}

# dns

resource "google_dns_record_set" "admin" {
  name         = "${local.admin_fqdn}."
  type         = "A"
  ttl          = 300
  managed_zone = var.dns_managed_zone
  rrdatas      = [google_compute_global_address.admin-ip.address]
}
