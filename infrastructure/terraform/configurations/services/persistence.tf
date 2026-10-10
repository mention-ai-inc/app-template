# document store
resource "google_firestore_database" "services-database" {
  count = local.is_production ? 1 : 0 # feature database handled in operations because it is shared

  project     = local.project
  name        = "(default)" # use the default firestore database for all services, namespace the collections
  location_id = var.preferred_region
  type        = "FIRESTORE_NATIVE"
}

resource "google_firestore_backup_schedule" "daily-backup" {
  count = local.is_production ? 1 : 0

  project   = local.project
  database  = google_firestore_database.services-database[0].name
  retention = "8467200s" # 14 weeks
  daily_recurrence {}
}

resource "google_firestore_field" "event-ttl" {
  for_each = toset(keys(var.services))

  project    = local.project
  database   = "(default)" # hard coded because we always use the default database
  collection = "${local.feature_environment}${each.value}_events"
  field      = "ttl"

  ttl_config {}

  depends_on = [google_firestore_database.services-database]
}

resource "google_firestore_field" "command-ttl" {
  for_each = toset(keys(var.services))

  project    = local.project
  database   = "(default)" # hard coded because we always use the default database
  collection = "${local.feature_environment}${each.value}_commands"
  field      = "ttl"

  ttl_config {}

  depends_on = [google_firestore_database.services-database]
}

resource "google_firestore_field" "audit-ttl" {
  for_each = toset(keys(var.services))

  project    = local.project
  database   = "(default)" # hard coded because we always use the default database
  collection = "${local.feature_environment}${each.value}_audit"
  field      = "ttl"

  ttl_config {}

  depends_on = [google_firestore_database.services-database]
}

# cache
data "google_secret_manager_secret_version_access" "redis_password" {
  secret = data.terraform_remote_state.operations.outputs.redis-password-secret-id
}

module "redis" {
  source = "../../modules/compute-engine-redis"

  project_id            = local.project
  operations_project_id = var.operations_project_id
  zone                  = local.instance_zone
  subnetwork            = data.terraform_remote_state.operations.outputs.instances-subnetwork-id
  environment_prefix    = local.feature_environment
  service_account_email = module.persistence-service-account.email

  max_memory     = var.redis_max_memory
  disk_size_gb   = var.redis_disk_size_gb
  machine_type   = local.redis_machine_type
  disk_image     = var.redis_disk_image
  is_production  = local.is_production
  redis_password = data.google_secret_manager_secret_version_access.redis_password.secret_data
}
