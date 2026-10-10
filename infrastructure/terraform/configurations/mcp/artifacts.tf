module "mcp-docker-images" {
  source = "../../modules/ecr-repository"

  repository_name = "${local.feature_environment}mcp"
  readers         = [module.mcp-task-role.arn, module.task-execution-role.arn]
}

output "mcp_repository_url" {
  description = "Repository the MCP server image is pushed to."
  value       = module.mcp-docker-images.repository_url
}
