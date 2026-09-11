resource "google_artifact_registry_repository" "mcp-docker-images" {
  description   = "This repository contains Docker images for the MCP server."
  format        = "DOCKER"
  location      = var.preferred_region
  project       = local.project
  repository_id = "${local.feature_environment}mcp"

  timeouts {}
}
