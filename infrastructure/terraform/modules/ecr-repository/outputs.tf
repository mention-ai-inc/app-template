output "repository_url" {
  description = "The URL images are pushed to and pulled from."
  value       = aws_ecr_repository.repository.repository_url
}

output "repository_arn" {
  description = "ARN of the repository."
  value       = aws_ecr_repository.repository.arn
}

output "repository_name" {
  description = "Name of the repository."
  value       = aws_ecr_repository.repository.name
}
