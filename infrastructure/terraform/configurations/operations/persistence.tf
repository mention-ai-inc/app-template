# firestore
resource "google_firestore_database" "feature-database" {
  project     = module.feature-project.project_id
  name        = "(default)" # use the default firestore database for all services, namespace the collections
  location_id = var.preferred_region
  type        = "FIRESTORE_NATIVE"
}

# redis
resource "google_secret_manager_secret" "redis-password" {
  secret_id = "REDIS_PASSWORD"

  replication {
    user_managed {
      replicas {
        location = "us-central1"
      }
    }
  }
}

resource "random_password" "redis-password-value" {
  length  = 32
  special = false
}

resource "google_secret_manager_secret_version" "redis-password-version" {
  secret      = google_secret_manager_secret.redis-password.id
  secret_data = random_password.redis-password-value.result
}

output "redis-password-secret-id" {
  value = google_secret_manager_secret.redis-password.id
}
