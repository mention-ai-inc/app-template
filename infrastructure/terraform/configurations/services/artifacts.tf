resource "google_artifact_registry_repository" "service-docker-images" {
  description   = "This repository contains Docker images for services."
  format        = "DOCKER"
  location      = var.preferred_region
  project       = local.project
  repository_id = "${local.feature_environment}services"

  timeouts {}
}
