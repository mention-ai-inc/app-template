resource "google_artifact_registry_repository" "docker-cache" {
  description   = "This repository contains cached layers for Docker images from all projects."
  format        = "DOCKER"
  location      = var.preferred_region
  project       = var.operations_project_id
  repository_id = "docker-cache"

  timeouts {}
}

resource "google_artifact_registry_repository" "public-images" {
  description   = "Private replicas of public Docker images for use by instances without external IPs."
  format        = "DOCKER"
  location      = var.preferred_region
  project       = var.operations_project_id
  repository_id = "public-images"

  timeouts {}
}
