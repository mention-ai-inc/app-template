module "docker-cache" {
  source = "../../modules/ecr-repository"

  repository_name = "docker-cache"
}

module "public-images" {
  source = "../../modules/ecr-repository"

  repository_name = "public-images"
}

output "docker_cache_repository_url" {
  value = module.docker-cache.repository_url
}

output "public_images_repository_url" {
  value = module.public-images.repository_url
}
