module "service-docker-images" {
  source = "../../modules/ecr-repository"

  repository_name = "${local.feature_environment}services"
  readers         = concat([for role in module.service-task-role : role.arn], [module.task-execution-role.arn])
}

output "service_repository_url" {
  description = "Repository every service image is pushed to."
  value       = module.service-docker-images.repository_url
}
